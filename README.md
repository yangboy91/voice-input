# 语音输入 (个人版 Wispr Flow)

按住热键说话 → 松开 → 自动转写、清洗、粘贴到当前光标处。中文优先。macOS 菜单栏应用。

**链路**：麦克风 → 阿里云 Paraformer 流式识别 → DeepSeek 语义清洗 → 模拟粘贴

> 个人项目，按自己需要做的，开源出来供参考 / 自用。PR welcome，但维护精力有限（低支持）。

**特点**：中文优先（Paraformer + DeepSeek，国内可达且便宜）· 上下文感知（读光标前文字自然衔接）· 自带 key、本地运行、用完即弃。

## 现状与限制（开源前的诚实交代）
- **macOS 限定**，且只在 Apple Silicon 上验证过。
- **依赖付费云 API**（阿里云 Paraformer + DeepSeek），不是开箱即用——需自己开通、填 key。还没有本地模型选项（FunASR/whisper 是合理的 roadmap）。
- **.app 未签名/未公证**：自己 build，首次运行要手动过 Gatekeeper + 授三个权限（详见下）。没有现成安装包。
- **源码路径**：默认从 `~/语音输入` 加载，可用环境变量 `VOICEINPUT_SRC` 覆盖。

## 安装

```bash
cd ~/语音输入
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# 编辑 .env 填入 DASHSCOPE_API_KEY 和 DEEPSEEK_API_KEY
```

### 申请 API key
- **DashScope（Paraformer）**: https://bailian.console.aliyun.com/ → API-KEY 管理。新用户有免费额度，之后约 ¥0.288/小时音频，按秒计费，个人用一个月几乎可忽略。
- **DeepSeek**: https://platform.deepseek.com/api_keys 。清洗一次几百 token，成本约几厘。

## 运行

日常用的是**独立 .app**：`~/语音输入/语音输入.app`，由 py2app 打包，自带 Python、独立身份（bundle id `com.steven.voiceinput`）。双击即开（菜单栏应用，无 Dock 图标），已配置**开机自启**（登录项「语音输入」）。

**关键架构：.app 只是固定外壳。** 入口是 `bootstrap.py`，运行时从 `~/语音输入/` 动态加载真正的业务代码（`app/config/context/asr/polish/output`，这些 *不* 打进 bundle）。好处：
- **改业务代码或 `config.py`（加词汇、app 映射、调 prompt）→ 只需重启 app，无需重新打包**。
- 外壳从不变 → 签名 hash 稳定 → 三个权限授一次永久有效（不会每次改动都掉权限）。

- 取消自启：系统设置 → 通用 → 登录项 → 移除「语音输入」。
- 重新加自启：
  ```bash
  osascript -e "tell application \"System Events\" to make login item at end with properties {path:\"$HOME/语音输入/语音输入.app\", hidden:true}"
  ```

### 改代码 / 改配置 → 只重启（日常）
直接编辑 `~/语音输入/*.py`，然后：
```bash
pkill -f "语音输入.app/Contents/MacOS"; open ~/语音输入/语音输入.app
```
`.env`（key）和所有 `.py` 都是外部加载，改完重启即可生效。

### 只有加了新的 pip 依赖时才重建外壳（极少）
```bash
source .venv/bin/activate && rm -rf build dist
arch -arm64 python setup.py py2app          # 必须 arm64
# 新依赖要加进 setup.py 的 packages/includes
pkill -f "语音输入.app/Contents/MacOS"; rm -rf 语音输入.app
cp -R dist/语音输入.app 语音输入.app && open 语音输入.app
```
> ⚠️ 重建外壳会改签名 hash，三个权限要重授一次（删掉旧的「语音输入」再按下面步骤重加）。这就是为什么尽量别重建外壳。

### 调试 —— 直接从终端跑源码
```bash
source .venv/bin/activate
python app.py        # 能看到 [启动]/[录音]/[转写]/[清洗] 实时输出
```
（从终端跑用的是 Terminal 的权限；独立 .app 用的是「语音输入」自己的权限。两套独立。）

### 权限（独立 .app 首次必做）
三个权限都授给 **「语音输入」**（一个身份管全部），系统设置 → 隐私与安全性：
1. **Accessibility（辅助功能）** — `+` → `Cmd+Shift+G` → `~/语音输入/语音输入.app` → 打开。（管模拟粘贴）
2. **Input Monitoring（输入监控）** — 同样添加 `~/语音输入/语音输入.app` → 打开。（管全局热键监听）
3. **Microphone（麦克风）** — 第一次按住 Option 录音时自动弹窗 → 允许。（管录音）

授权 1、2 后**必须重启 app**（trust 在启动时检查）。

> 注意：🎤 图标可能被刘海/溢出区挡住，不影响打字（热键是全局的）。按住 Cmd 拖动菜单栏图标可重新排列；图标太多可装 Ice/Bartender。

## 用法
- **按住 Option 键**（左右都行）说话，松开即出字。
- 菜单栏图标：🎤 就绪 / 🔴 录音中 / ⏳ 处理中。
- 从终端运行时，会打印 `[录音]/[转写]/[清洗]` 方便看链路。
- 菜单里可临时关掉「语义清洗」，直接出原始转写（更快、零额外成本）。

## 上下文感知（`context.py`）
三个特性，全部折叠进同一次清洗调用（不加额外往返、不联网额外服务），**只在「语义清洗」开着时生效**，菜单「上下文感知」可总开关：
- **读光标前文字** — 用 macOS Accessibility 读焦点框光标前最多 `PRECEDING_CHARS`(默认300) 字，喂给清洗让新句自然接上文。读不到（部分 Electron/网页框）就静默跳过。
- **最近口述记忆** — 滚动缓冲（`HISTORY_SIZE`/`HISTORY_WINDOW_SEC`，默认最近3条/180秒），连续说话时统一术语语气。仅内存、用完即弃。
- **前台 app 适配** — 按 `APP_PROFILES`（bundle id → `{style, vocab}`）自动套风格/补充词汇。默认空 = 不打扰，风格仍由菜单手动选。

## 自定义
都在 `config.py`（改完**只需重启 app**，不用重新打包）：
- `HOTKEY_KEYCODES` — 换热键，用 macOS 键码。左Option=58 右Option=61 左Cmd=55 右Cmd=54 左Ctrl=59 右Ctrl=62。默认 `{58, 61}`（任意 Option）。注意 **fn 键 pynput 抓不到，不能用**。
- `POLISH_STYLES` / `POLISH_STYLE` — 清洗风格（书面/口语/邮件），菜单栏可实时切换，改默认值在此。
- `VOCAB` — 专属词汇表（人名/术语），列在这里的词清洗时原样保留、不被纠错。
- `APP_PROFILES` — 按 app 自动套风格/词汇，如 `{"com.apple.mail": {"style": "邮件"}}`。
- `CONTEXT_ENABLED` / `PRECEDING_CHARS` / `HISTORY_SIZE` / `HISTORY_WINDOW_SEC` — 上下文感知开关与参数。
- `POLISH_ENABLED` — 默认是否开清洗。

## 踩过的坑（已在代码里修好）
- **SSL CERTIFICATE_VERIFY_FAILED**：python.org 版 Python 没装根证书，dashscope 流式(aiohttp)连不上。`config.py` 顶部用 certifi 给 `ssl.create_default_context` 打了补丁（带 try/except，避免打包后 httpx 传错 cafile 时崩），且必须早于 dashscope 导入（所以 `asr.py` 先 import config）。
- **热键不触发**：pynput 在本机把 Option 报成通用 `Key.alt`，按枚举名匹配会漏。改成按 macOS 键码匹配。
- **三个独立权限**：粘贴要 **Accessibility**、监听热键要 **Input Monitoring**、录音要 **Microphone**——macOS 把它们当三件事，要分别授权。
- **为什么打成独立 .app**：手搓 .app 跑的是共享的框架 `Python.app`，**麦克风权限注册不进去**（麦克风列表没有 `+` 不能手动加）。用 py2app 打成自带 Python 的独立 bundle（有 `NSMicrophoneUsageDescription` + 独立 bundle id），三个权限才能干净地归到「语音输入」一个身份，麦克风也能正常弹窗注册。
- **py2app 两个坑**：`_sounddevice_data` 要加进 `packages`（否则 libportaudio.dylib 被压进 zip 没法 dlopen）；打包必须 `arch -arm64`（否则 C 扩展架构不匹配）。
- **重打包掉权限**：adhoc 签名的 .app 每次重建签名 hash 都变，TCC 把它当新 app，三个权限全掉。解法：用 `bootstrap.py` 固定外壳 + 外部加载业务代码，让改代码不触发重建，hash 稳定、权限常驻。代价：外部代码的依赖 modulegraph 探测不到，要全部显式列进 `setup.py`（如 `pyperclip`）。

## 文件结构
| 文件 | 作用 |
|------|------|
| `bootstrap.py` | py2app 固定入口外壳；运行时从项目目录动态加载 `app` |
| `app.py` | 菜单栏 + 热键 + 录音编排 + 上下文采集编排 |
| `asr.py` | Paraformer 流式识别封装 |
| `polish.py` | DeepSeek 语义清洗（可带上下文；失败自动回退原文） |
| `context.py` | 读光标前文字(AX) + 前台 app 识别 + 口述历史 |
| `output.py` | 写剪贴板 + 模拟 Cmd+V 粘贴 |
| `config.py` | 所有配置 + SSL 补丁 + 清洗风格/词汇表/上下文参数 |
| `setup.py` | py2app 打包脚本（外壳 + 第三方依赖白名单） |

## 已知取舍
- 用「粘贴」而非逐字打字：中文逐字会触发输入法，粘贴最稳；会短暂占用剪贴板（用完自动恢复）。
- 录音用 hold-to-talk：松开才转写，不是边说边出（实现简单、可控）。想要边说边显示可后续加。
- 清洗有 ~0.5-1.5s 延迟。追求极速可在菜单里关掉清洗。
