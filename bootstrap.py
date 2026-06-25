"""py2app 的固定入口外壳 / Fixed py2app entry shell.

它本身几乎不变，所以打包出的 .app 签名 hash 稳定，授过的权限一直有效。
真正的应用代码在源码目录下，运行时动态加载——改代码只需重启，无需重新打包。
(用 importlib 动态导入，py2app 的 modulegraph 不会把这些源码打进 bundle，
 从而保证它们始终从外部目录读取。第三方依赖仍打进 bundle，见 setup.py。)

English: A stable shell whose code never changes, so the bundle's signature
stays constant and granted permissions persist. The real app code lives in the
source directory and is loaded at runtime via importlib (so modulegraph does not
bundle it) — edit code and just restart, no rebuild needed.

源码目录解析顺序 / Source dir resolution order:
  1. 环境变量 VOICEINPUT_SRC / env var VOICEINPUT_SRC
  2. build.sh 写的指针文件 / pointer file written by build.sh
  3. 兜底 ~/语音输入 / fallback ~/语音输入
"""
import os
import sys
import importlib

_POINTER = os.path.expanduser("~/Library/Application Support/voiceinput/src_path")


def _read_pointer():
    try:
        with open(_POINTER) as f:
            d = f.read().strip()
            return d if d and os.path.isdir(d) else None
    except Exception:
        return None


PROJECT_DIR = (
    os.environ.get("VOICEINPUT_SRC")
    or _read_pointer()
    or os.path.expanduser("~/语音输入")
)

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

app_module = importlib.import_module("app")
app_module.VoiceInputApp().run()
