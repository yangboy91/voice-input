#!/bin/bash
# 一键构建 + 安装 语音输入.app / One-command build + install.
#
#   ./build.sh
#
# 干什么 / What it does:
#   1. 建虚拟环境、装依赖 / create venv, install deps
#   2. py2app 打包（Apple Silicon 用 arm64）/ build the .app
#   3. ad-hoc 签名 / ad-hoc codesign
#   4. 记录源码目录，安装 .app 到仓库目录 / record source dir, install .app
#
# 之后 / Then: 授三个权限（见 README），双击 语音输入.app。
# 改代码只需重启 app，不必重跑本脚本（外壳从源码目录动态加载）。
# Edit code → just restart the app; no rebuild needed (shell loads code at runtime).

set -e
REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"

echo "==> 源码目录 / Source dir: $REPO"

# --- 1. venv + deps ---
if [ ! -d ".venv" ]; then
  echo "==> 创建虚拟环境 / Creating venv"
  python3 -m venv .venv
fi
source .venv/bin/activate
echo "==> 安装依赖 / Installing dependencies"
pip install -q --upgrade pip
pip install -q -r requirements.txt
pip install -q py2app

# --- 2. 打包 / build ---
echo "==> 打包 .app / Building .app"
rm -rf build dist
if [ "$(uname -m)" = "arm64" ]; then
  arch -arm64 python setup.py py2app
else
  echo "    (非 Apple Silicon / not arm64 — 直接构建)"
  python setup.py py2app
fi

APP="dist/语音输入.app"
[ -d "$APP" ] || { echo "❌ 构建失败：找不到 $APP"; exit 1; }

# --- 3. ad-hoc 签名 / sign ---
echo "==> ad-hoc 签名 / Ad-hoc signing"
codesign --force --deep --sign - "$APP" 2>/dev/null || true

# --- 4. 记录源码目录 + 安装 / record source + install ---
SUPPORT="$HOME/Library/Application Support/voiceinput"
mkdir -p "$SUPPORT"
printf '%s' "$REPO" > "$SUPPORT/src_path"
echo "==> 已记录源码目录到 $SUPPORT/src_path"

echo "==> 安装到 $REPO/语音输入.app"
pkill -f "语音输入.app/Contents/MacOS" 2>/dev/null || true
sleep 1
rm -rf "$REPO/语音输入.app"
cp -R "$APP" "$REPO/语音输入.app"
rm -rf build dist

echo ""
echo "✅ 构建完成 / Done.  双击 $REPO/语音输入.app 运行。"
echo ""
echo "首次需在 系统设置 → 隐私与安全性 给「语音输入」授三个权限 / First run, grant 3 permissions:"
echo "  • Accessibility（辅助功能）   — 模拟粘贴 / paste"
echo "  • Input Monitoring（输入监控）— 全局热键 / hotkey"
echo "  • Microphone（麦克风）        — 录音（首次自动弹窗）/ recording"
echo "授权 Accessibility/Input Monitoring 后需重启 app / Restart app after granting the first two."
