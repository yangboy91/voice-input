"""py2app 的固定入口外壳。

它本身几乎不变，所以打包出的 .app 签名 hash 稳定，授过的权限一直有效。
真正的应用代码在 ~/语音输入/ 下，运行时动态加载——改代码只需重启，无需重新打包。
(用 importlib 动态导入，py2app 的 modulegraph 不会把这些源码打进 bundle，
 从而保证它们始终从外部目录读取。第三方依赖仍打进 bundle，见 setup.py。)
"""
import sys
import importlib

PROJECT_DIR = "/Users/stevenyang/语音输入"

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

app_module = importlib.import_module("app")
app_module.VoiceInputApp().run()
