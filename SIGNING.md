# 签名与公证 / Code Signing & Notarization

三个层次，按你的需求选 / Three levels, pick what you need:

---

## 1. Ad-hoc 签名（默认，`build.sh` 已做）/ Ad-hoc (default)

`build.sh` 用 `codesign --sign -` 做 ad-hoc 签名。**自己 build、自己用，足够。**
首次运行 macOS Gatekeeper 可能拦一下：右键 .app → 打开，或在「系统设置 → 隐私与安全性」点「仍要打开」。

`build.sh` ad-hoc signs the app. **Enough if you build and run it yourself.**
On first launch, if Gatekeeper blocks it: right-click the app → Open, or allow it in
System Settings → Privacy & Security.

> ⚠️ Ad-hoc 签名每次重 build 的 hash 都变，会被 TCC 当成"新 app"，三个权限要重授。
> 本项目用「固定外壳 + 源码外部加载」规避了这点：改代码只重启、不重 build，所以权限不掉。
> Ad-hoc hash changes per build, so TCC re-prompts. This project avoids that by loading
> code from the source dir at runtime — edit & restart instead of rebuilding.

---

## 2. 自签名证书（可选，让重 build 也不掉权限）/ Self-signed cert (optional)

如果你经常要重 build 外壳，又不想每次重授权，用一张固定的自签名证书签名，
TCC 就按证书认身份、跨 build 稳定。最简单的方式是用「钥匙串访问」GUI 建证书：

If you rebuild the shell often, sign with a stable self-signed certificate so TCC
keys on the cert identity and grants persist across rebuilds. Easiest via Keychain Access:

1. 钥匙串访问 → 证书助理 → 创建证书 / Keychain Access → Certificate Assistant → Create a Certificate
2. 名称 `VoiceInput`，类型「代码签名」/ Name `VoiceInput`, type "Code Signing", self-signed
3. 签名时用它 / Sign with it:
   ```bash
   codesign --force --deep --sign "VoiceInput" 语音输入.app
   ```

---

## 3. 公证（分发给别人时才需要）/ Notarization (only to distribute a prebuilt app)

要把**打包好的 .app 直接发给别人**且不让对方手动过 Gatekeeper，需要 Apple 公证。
**这需要你自己的 Apple 开发者账号（$99/年）和你的凭据** —— 项目作者无法代办。

To ship a **prebuilt .app to others** without Gatekeeper friction, Apple notarization
is required. **This needs your own Apple Developer account ($99/yr) and credentials.**

步骤概览 / Steps (run with your own account):
```bash
# 1. 用你的 "Developer ID Application" 证书签名（带 hardened runtime）
codesign --force --deep --options runtime --sign "Developer ID Application: Your Name (TEAMID)" 语音输入.app

# 2. 打包成 zip
ditto -c -k --keepParent 语音输入.app 语音输入.zip

# 3. 提交公证（先 xcrun notarytool store-credentials 存好你的凭据）
xcrun notarytool submit 语音输入.zip --keychain-profile "notary" --wait

# 4. 装订票据
xcrun stapler staple 语音输入.app
```

> 大多数自用场景用第 1 层就够了。公证只在做公开分发安装包时才需要。
> Level 1 is enough for personal use. Notarization only matters for public binary distribution.
