"""py2app 打包脚本：把语音输入打成自带 Python 的独立 .app。

构建：
    source .venv/bin/activate
    python setup.py py2app
产物在 dist/语音输入.app
"""
import sys

from setuptools import setup

# py2app 的 modulegraph 遍历大依赖图(openai/dashscope/pydantic 等)可能爆默认递归栈，
# 调高上限规避 RecursionError。
sys.setrecursionlimit(10000)

# 入口是固定外壳 bootstrap.py（运行时从项目目录动态加载真正的 app 代码），
# 这样改业务代码不必重新打包，bundle 签名 hash 保持稳定、权限不掉。
APP = ["bootstrap.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,
    "packages": [
        "rumps",
        "pynput",
        "sounddevice",
        "_sounddevice_data",  # 不压缩，否则 libportaudio.dylib 在 zip 里无法 dlopen
        "dashscope",
        "openai",
        "certifi",
        "dotenv",
        "pyperclip",
    ],
    # 注意：业务源码(app/config/context/asr/polish/output)故意 NOT 列在这里，
    # 它们运行时从项目目录加载。只把第三方依赖打进 bundle。
    "includes": [
        "_cffi_backend",
        # pyobjc 框架——业务代码里懒加载，modulegraph 探测不到，显式包含
        "ApplicationServices",
        "AppKit",
        "Quartz",
        "Foundation",
    ],
    "plist": {
        "CFBundleName": "语音输入",
        "CFBundleDisplayName": "语音输入",
        "CFBundleIdentifier": "com.steven.voiceinput",
        "CFBundleVersion": "1.0",
        "CFBundleShortVersionString": "1.0",
        # 菜单栏应用，无 Dock 图标
        "LSUIElement": True,
        # 麦克风用途说明——有了它，独立 .app 才能正常注册麦克风权限
        "NSMicrophoneUsageDescription": "语音输入需要使用麦克风进行语音转写。",
        "LSMinimumSystemVersion": "11.0",
    },
}

setup(
    name="VoiceInput",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
