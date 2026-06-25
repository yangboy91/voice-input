"""上下文采集：读光标前文字、识别前台 app、滚动口述历史。

全部走本地 macOS API（Accessibility / AppKit），不联网、用完即弃。
任何读取失败都安静返回 None/空，绝不影响主流程。
"""
import time
from collections import deque

import config


# ---------- 光标前文字（Accessibility） ----------
def read_preceding_text(max_chars: int) -> str | None:
    """读当前焦点输入框里、光标之前的文字（最多 max_chars 个字）。
    依赖辅助功能权限（app 已有）。读不到就返回 None——很多 app（部分
    Electron/网页输入框）不暴露文本，属正常，直接跳过即可。"""
    try:
        from ApplicationServices import (
            AXUIElementCreateSystemWide,
            AXUIElementCopyAttributeValue,
            AXValueGetValue,
            kAXFocusedUIElementAttribute,
            kAXValueAttribute,
            kAXSelectedTextRangeAttribute,
            kAXValueCFRangeType,
        )

        system = AXUIElementCreateSystemWide()
        err, focused = AXUIElementCopyAttributeValue(
            system, kAXFocusedUIElementAttribute, None
        )
        if err != 0 or focused is None:
            return None

        err, value = AXUIElementCopyAttributeValue(focused, kAXValueAttribute, None)
        if err != 0 or not isinstance(value, str) or not value:
            return None

        # 光标位置（选区起点）。读不到就退化为"取整段文本的末尾 max_chars"。
        loc = len(value)
        err, sel = AXUIElementCopyAttributeValue(
            focused, kAXSelectedTextRangeAttribute, None
        )
        if err == 0 and sel is not None:
            ok, rng = AXValueGetValue(sel, kAXValueCFRangeType, None)
            if ok and rng is not None:
                try:
                    loc = int(rng.location)
                except Exception:
                    try:
                        loc = int(rng[0])
                    except Exception:
                        loc = len(value)

        preceding = value[:loc] if 0 <= loc <= len(value) else value
        preceding = preceding[-max_chars:].strip()
        return preceding or None
    except Exception:
        return None


# ---------- 前台 app ----------
def frontmost_app_bundle_id() -> str | None:
    try:
        from AppKit import NSWorkspace

        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        return app.bundleIdentifier() if app else None
    except Exception:
        return None


def app_profile(bundle_id: str | None) -> dict:
    """根据前台 app 返回 {style, vocab} 配置；没配置就返回空 dict。"""
    if not bundle_id:
        return {}
    return config.APP_PROFILES.get(bundle_id, {})


# ---------- 口述历史（滚动缓冲，仅内存） ----------
class DictationHistory:
    def __init__(self, size: int, window_sec: int):
        self.window = window_sec
        self._items = deque(maxlen=max(1, size))  # (timestamp, text)

    def add(self, text: str):
        if text and text.strip():
            self._items.append((time.time(), text.strip()))

    def recent(self) -> list[str]:
        now = time.time()
        return [t for (ts, t) in self._items if now - ts <= self.window]
