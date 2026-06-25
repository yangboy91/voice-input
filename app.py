"""语音输入 — macOS 菜单栏原型。

按住热键(默认右 Option)说话 → 松开 → Paraformer 转写 → DeepSeek 清洗 → 粘贴到光标处。

运行: python app.py
需要授予：麦克风权限 + 辅助功能(Accessibility)权限。
"""
import threading

import rumps
import sounddevice as sd
from pynput import keyboard

import config
import context
from asr import ParaformerSession
from polish import polish
from output import paste_text

def keycode_of(key):
    """从 pynput 的按键对象里取出 macOS 键码(keycode)。
    特殊键(Option/Cmd 等)在 key.value.vk，普通字符键在 key.vk。"""
    val = getattr(key, "value", None)
    if val is not None and getattr(val, "vk", None) is not None:
        return val.vk
    return getattr(key, "vk", None)


IDLE_TITLE = "🎤"
REC_TITLE = "🔴"
BUSY_TITLE = "⏳"


class VoiceInputApp(rumps.App):
    def __init__(self):
        super().__init__("语音输入", title=IDLE_TITLE, quit_button="退出")
        self.polish_item = rumps.MenuItem("语义清洗 (DeepSeek)", callback=self.toggle_polish)
        self.polish_item.state = config.POLISH_ENABLED
        self.context_item = rumps.MenuItem("上下文感知", callback=self.toggle_context)
        self.context_item.state = config.CONTEXT_ENABLED
        self.status_item = rumps.MenuItem("就绪", callback=None)

        # 清洗风格子菜单：单选，点谁切到谁
        self._style_items = {}
        for name in config.POLISH_STYLES:
            item = rumps.MenuItem(name, callback=self.choose_style)
            item.state = (name == config.POLISH_STYLE)
            self._style_items[name] = item
        style_menu = rumps.MenuItem("清洗风格")
        style_menu.update(list(self._style_items.values()))

        self.menu = [self.status_item, None, self.polish_item, self.context_item, style_menu]

        self._recording = False
        self._lock = threading.Lock()
        self._session = None
        self._stream = None
        self._history = context.DictationHistory(
            config.HISTORY_SIZE, config.HISTORY_WINDOW_SEC
        )

        self._hotkey_codes = set(config.HOTKEY_KEYCODES)
        self._listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release
        )
        self._listener.start()
        print(f"[启动] 菜单栏已就绪，热键={config.HOTKEY_NAME} 键码{self._hotkey_codes}，监听中。按住该键说话。")

        self._check_keys()

    # ---------- 配置/状态 ----------
    def _check_keys(self):
        missing = []
        if not config.DASHSCOPE_API_KEY:
            missing.append("DASHSCOPE_API_KEY")
        if config.POLISH_ENABLED and not config.DEEPSEEK_API_KEY:
            missing.append("DEEPSEEK_API_KEY")
        if missing:
            self.status_item.title = "缺少: " + ", ".join(missing)
            self._notify("配置缺失", "请在 .env 填入: " + ", ".join(missing))

    def toggle_polish(self, sender):
        sender.state = not sender.state
        config.POLISH_ENABLED = bool(sender.state)

    def toggle_context(self, sender):
        sender.state = not sender.state
        config.CONTEXT_ENABLED = bool(sender.state)

    def choose_style(self, sender):
        config.POLISH_STYLE = sender.title
        for name, item in self._style_items.items():
            item.state = (name == sender.title)
        print(f"[风格] 切换为「{sender.title}」")

    # ---------- 热键 ----------
    def _on_press(self, key):
        code = keycode_of(key)
        if code in self._hotkey_codes and not self._recording:
            self._start_recording()

    def _on_release(self, key):
        code = keycode_of(key)
        if code in self._hotkey_codes and self._recording:
            self._stop_recording()

    # ---------- 录音 ----------
    def _start_recording(self):
        with self._lock:
            if self._recording:
                return
            try:
                self._session = ParaformerSession()
                self._session.start()
                self._stream = sd.RawInputStream(
                    samplerate=config.SAMPLE_RATE,
                    blocksize=config.BLOCK_SIZE,
                    dtype=config.DTYPE,
                    channels=config.CHANNELS,
                    callback=self._audio_callback,
                )
                self._stream.start()
                self._recording = True
                self.title = REC_TITLE
                self.status_item.title = "录音中…"
                print("[录音] 开始，说话中…")
            except Exception as e:
                self._cleanup_stream()
                print(f"[错误] 启动录音失败: {e}")
                self._notify("启动录音失败", str(e))

    def _audio_callback(self, indata, frames, time_info, status):
        if self._recording and self._session is not None:
            self._session.feed(bytes(indata))

    def _stop_recording(self):
        with self._lock:
            if not self._recording:
                return
            self._recording = False
        self.title = BUSY_TITLE
        self.status_item.title = "转写中…"
        # 处理放到后台线程，避免卡住热键监听
        threading.Thread(target=self._process, daemon=True).start()

    def _process(self):
        try:
            self._cleanup_stream()
            err = None
            if self._session:
                text = self._session.stop()
                err = self._session.last_error
            else:
                text = ""
            self._session = None
            print(f"[转写] {text!r}" + (f"  [错误] {err}" if err else ""))
            if not text:
                self.status_item.title = ("识别出错" if err else "没听到内容")
                self.title = IDLE_TITLE
                return
            if config.POLISH_ENABLED:
                self.status_item.title = "清洗中…"
                # 上下文只在清洗开着时采集并喂进同一次调用（不加额外往返）
                preceding = recent = style = extra_vocab = None
                if config.CONTEXT_ENABLED:
                    profile = context.app_profile(context.frontmost_app_bundle_id())
                    style = profile.get("style")
                    extra_vocab = profile.get("vocab")
                    preceding = context.read_preceding_text(config.PRECEDING_CHARS)
                    recent = self._history.recent()
                    print(f"[上下文] app风格={style} 光标前={len(preceding or '')}字 历史={len(recent or [])}条")
                text = polish(text, preceding_text=preceding, recent=recent,
                              style=style, extra_vocab=extra_vocab)
                print(f"[清洗] {text!r}")
            paste_text(text)
            self._history.add(text)
            preview = text[:20] + ("…" if len(text) > 20 else "")
            self.status_item.title = "已输入: " + preview
        except Exception as e:
            self._notify("处理失败", str(e))
            self.status_item.title = "出错: " + str(e)[:30]
        finally:
            self.title = IDLE_TITLE

    def _cleanup_stream(self):
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    # ---------- 工具 ----------
    def _notify(self, title, msg):
        try:
            rumps.notification("语音输入", title, msg)
        except Exception:
            print(f"[{title}] {msg}")


if __name__ == "__main__":
    VoiceInputApp().run()
