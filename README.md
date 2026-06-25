# 语音输入 · Voice Input

> 个人版 Wispr Flow / Typeless ——按住热键说话，自动转写、清洗、粘贴到光标处。中文优先，macOS 菜单栏应用。
>
> A personal Wispr Flow / Typeless ——hold a hotkey, speak, and get clean text pasted at your cursor. Chinese-first, macOS menu-bar app.

**链路 / Pipeline:** 麦克风 Mic → 语音识别 ASR → LLM 语义清洗 LLM polish → 模拟粘贴 paste-at-cursor

**亮点 / Highlights**
- 🇨🇳 **中文优先** —— 默认用 Paraformer + DeepSeek，国内可达、极便宜。Chinese-first stack that Western tools ignore.
- 🧠 **上下文感知** —— 读光标前文字，新句自然衔接上文；记住最近口述统一术语；按 app 自动切风格。Context-aware: reads text before the cursor so new dictation flows naturally.
- 🔌 **后端可换** —— 云端（便宜）或**全本地离线**（免 key、免联网）。Cloud or fully-local offline backends.
- 🪶 **菜单栏轻应用**，开机自启，按住 Option 即用。Lightweight menu-bar app with login-at-startup.

> ⚠️ 个人项目，按自己需要做的，开源供参考/自用。PR welcome，但维护精力有限（低支持）。
> A personal project, open-sourced for reference / self-use. PRs welcome, but low-support.

---

## 两种后端 / Two backend modes

| | 语音识别 ASR | 语义清洗 Polish | 成本 Cost | 需要 Needs |
|---|---|---|---|---|
| **云端 Cloud**（默认 default） | 阿里云 Paraformer | DeepSeek | 极低 ~¢/次 | API key |
| **本地 Local** | mlx-whisper | Ollama | 免费 Free | 自装模型 self-host models |

云端中文最准、最省心；本地完全离线、免 key。可分别选（如本地识别 + 云端清洗）。
Cloud is most accurate & turnkey; local is fully offline & key-free. Mix freely.

切换 / Switch in `config.py`: `ASR_BACKEND` = `"paraformer"`|`"local"`，`POLISH_BACKEND` = `"deepseek"`|`"ollama"`。

---

## 快速开始 / Quick start

```bash
git clone https://github.com/yangboy91/voice-input.git
cd voice-input
./build.sh                 # 建环境、打包、签名、安装 / setup, build, sign, install
cp .env.example .env       # 仅云端后端需要 / only for cloud backends
# 编辑 .env 填 key / edit .env with your keys
```

`build.sh` 完成后双击生成的 `语音输入.app`。首次需授权（见下）。
After `build.sh`, double-click the generated `语音输入.app`. Grant permissions on first run.

### 申请 key（仅云端） / Get keys (cloud only)
- **DashScope / Paraformer**: https://bailian.console.aliyun.com/ → API-KEY。新用户有免费额度，之后约 ¥0.288/小时音频。Free tier, then ~¥0.288/audio-hour.
- **DeepSeek**: https://platform.deepseek.com/api_keys 。每次清洗几厘。Fractions of a cent per polish.

### 走本地（免 key） / Go local (no keys)
```bash
source .venv/bin/activate
pip install -r requirements-local.txt          # 本地识别 / local ASR (mlx-whisper)
# 本地清洗 / local polish: 装 Ollama (https://ollama.com) 然后 ollama pull qwen2.5
# 在 config.py 设 ASR_BACKEND="local" / POLISH_BACKEND="ollama"，重启 app
```

---

## 权限（首次必做） / Permissions (required on first run)

三个权限都授给 **「语音输入」**，系统设置 → 隐私与安全性。
Grant all three to **语音输入** in System Settings → Privacy & Security.

| 权限 Permission | 作用 For | 怎么给 How |
|---|---|---|
| **Accessibility** 辅助功能 | 模拟粘贴 paste | `+` → `~/语音输入/语音输入.app` → 打开 |
| **Input Monitoring** 输入监控 | 全局热键 hotkey | 同上 same |
| **Microphone** 麦克风 | 录音 recording | 首次录音自动弹窗 auto-prompts |

授权前两个后**重启 app** 生效（trust 在启动时检查）。
Restart the app after granting the first two (trust is checked at launch).

> 🎤 图标可能被刘海/溢出区挡住，不影响打字（热键全局生效）。装 Ice/Bartender 可整理。
> The menu-bar icon may hide behind the notch; doesn't affect dictation (the hotkey is global).

---

## 用法 / Usage

- **按住 Option 键**（左右都行）说话，松开即出字。**Hold Option**, speak, release → text appears.
- 菜单栏图标 / Icon: 🎤 就绪 idle · 🔴 录音 recording · ⏳ 处理 processing
- 菜单项 / Menu: 「语义清洗」开关、「上下文感知」开关、「清洗风格」（书面/口语/邮件）。
  Toggle polish, toggle context-awareness, pick style (written / spoken / email).

---

## 配置 / Configuration

都在 `config.py`，**改完只需重启 app，不必重打包**（见架构）。All in `config.py`; edit & restart, no rebuild.

| 项 Key | 说明 |
|---|---|
| `ASR_BACKEND` / `POLISH_BACKEND` | 选后端 / pick cloud vs local |
| `HOTKEY_KEYCODES` | 热键键码 / hotkey (左Option=58 右Option=61 右Cmd=54…；fn 不可用 fn unsupported) |
| `POLISH_STYLES` / `POLISH_STYLE` | 清洗风格 / polishing styles (menu-switchable) |
| `VOCAB` | 专属词汇表：**既偏置 ASR 让名字/术语听得对，也在清洗时不被纠错** / glossary that both biases the ASR (hot words) and is preserved during polish |
| `HOTWORDS_ENABLED` / `HOTWORD_WEIGHT` | 热词偏置开关与权重(1-5) / ASR biasing toggle & weight |
| `APP_PROFILES` | 按 app 自动套风格/词汇 / per-app style & vocab |
| `LOCAL_ASR_MODEL` / `OLLAMA_MODEL` | 本地模型名 / local model names |
| `CONTEXT_ENABLED`, `PRECEDING_CHARS`, `HISTORY_SIZE` | 上下文参数 / context params |

> **热词偏置 / Hot-word biasing:** 往 `VOCAB` 里加人名/术语后，云端会自动建 Paraformer 热词表(`vocabulary_id`，按内容缓存)、本地会拼成 Whisper `initial_prompt`——让这些词在**识别第一步**就听对，而不是事后补救。`VOCAB` 为空时零副作用。Add names/terms to `VOCAB` and they bias the recognizer itself (Paraformer hot words / Whisper initial_prompt), fixing them at the source.

---

## 架构：为什么改代码不用重打包 / Architecture: edit without rebuilding

`.app` 是个**固定外壳**（`bootstrap.py` 入口 + 打包好的 Python 依赖）；真正的业务代码运行时从源码目录动态加载。
The `.app` is a **fixed shell** (`bootstrap.py` + bundled deps); the real code loads from the source dir at runtime.

- **改代码/配置 → 只重启 app**（`pkill -f 语音输入.app/Contents/MacOS; open ~/语音输入/语音输入.app`）。Edit → restart.
- 外壳不变 → 签名 hash 稳定 → **权限授一次永久有效**。Stable signature → permissions persist.
- 只有加新 pip 依赖才需重跑 `./build.sh`。Only rebuild when adding pip deps.
- 源码目录解析：`VOICEINPUT_SRC` 环境变量 → build.sh 写的指针文件 → `~/语音输入`。

签名与公证见 [SIGNING.md](SIGNING.md)。Signing & notarization: see [SIGNING.md](SIGNING.md).

---

## 现状与限制 / Status & limitations

- **macOS 限定**，仅在 Apple Silicon 验证过。macOS only, tested on Apple Silicon.
- **未公证**：自己 build，首次过一下 Gatekeeper。Not notarized; self-build, clear Gatekeeper once.
- 云端后端需自开通付费 API；本地后端需自装模型（实验性，欢迎反馈）。Cloud needs paid APIs; local backends are experimental.
- 单用户、菜单栏工具，非企业级。Single-user menu-bar tool.

---

## 文件结构 / Layout

| 文件 File | 作用 Purpose |
|---|---|
| `bootstrap.py` | 固定外壳入口，运行时加载 `app` / fixed shell entry |
| `app.py` | 菜单栏 + 热键 + 录音/上下文编排 / menu bar, hotkey, orchestration |
| `asr.py` / `asr_local.py` | 云 Paraformer / 本地 Whisper 识别 / cloud & local ASR |
| `hotwords.py` | VOCAB→ASR 偏置（热词/initial_prompt）/ bias ASR toward VOCAB |
| `polish.py` | DeepSeek/Ollama 语义清洗 / pluggable polish |
| `context.py` | 读光标前文字 + app 识别 + 历史 / context capture |
| `output.py` | 剪贴板 + 模拟粘贴 / clipboard paste |
| `config.py` | 全部配置 + SSL 补丁 / all config |
| `setup.py` / `build.sh` | 打包 / build |

---

## License

MIT — see [LICENSE](LICENSE).
