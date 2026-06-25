"""把最终文本输出到当前光标处：写剪贴板 + 模拟 Cmd+V 粘贴。

为什么用粘贴而不是逐字"打字"：中文逐字输入会触发输入法、又慢又乱，
直接粘贴最稳。粘贴后恢复用户原来的剪贴板内容，避免污染。
"""
import time

import pyperclip
from pynput.keyboard import Controller, Key

_kbd = Controller()


def paste_text(text: str, restore_clipboard: bool = True):
    text = text.strip()
    if not text:
        return

    old_clip = None
    if restore_clipboard:
        try:
            old_clip = pyperclip.paste()
        except Exception:
            old_clip = None

    pyperclip.copy(text)
    time.sleep(0.05)  # 给剪贴板写入一点时间

    # 模拟 Cmd+V
    with _kbd.pressed(Key.cmd):
        _kbd.press("v")
        _kbd.release("v")

    if restore_clipboard and old_clip is not None:
        time.sleep(0.2)  # 等粘贴完成再恢复
        try:
            pyperclip.copy(old_clip)
        except Exception:
            pass
