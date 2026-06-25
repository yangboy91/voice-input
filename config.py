"""集中管理配置：API key、热键、音频参数、清洗 prompt。"""
import os
import ssl
from pathlib import Path
import certifi
from dotenv import load_dotenv

# python.org 版 Python 默认没装根证书，dashscope 流式(aiohttp)会 SSL 验证失败
# (CERTIFICATE_VERIFY_FAILED)。强制每个默认 SSL 上下文都加载 certifi 证书。
# 必须在任何网络库建连接前执行——config 被最先 import，放这里最稳。
_orig_create_default_context = ssl.create_default_context


def _create_default_context_with_certifi(*args, **kwargs):
    try:
        ctx = _orig_create_default_context(*args, **kwargs)
    except Exception:
        # 调用方(如 httpx)传了不存在的 cafile/capath——打包后路径错位时会这样。
        # 退回到干净 context，下面统一用 certifi 的证书。
        ctx = _orig_create_default_context()
    try:
        ctx.load_verify_locations(certifi.where())
    except Exception:
        pass
    return ctx


ssl.create_default_context = _create_default_context_with_certifi
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

# 用绝对路径加载 .env，这样从 .app/launchd 启动（工作目录是 /）也能找到 key。
# 打包成独立 .app 后 __file__ 在 bundle 里没有 .env，所以也回退到项目目录。
_env_candidates = [Path(__file__).resolve().parent / ".env"]
if os.environ.get("VOICEINPUT_SRC"):
    _env_candidates.append(Path(os.environ["VOICEINPUT_SRC"]) / ".env")
_env_candidates.append(Path.home() / "语音输入" / ".env")
for _env in _env_candidates:
    if _env.exists():
        load_dotenv(_env)
        break

# ---- API keys ----
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# ---- ASR 后端选择 ----
# "paraformer" = 阿里云 Paraformer 云端流式（默认，中文最佳、极便宜，需 key）
# "local"      = 本地 mlx-whisper（离线、免费、免 key；需 requirements-local.txt）
ASR_BACKEND = "paraformer"

# ---- ASR (阿里云 Paraformer 流式) ----
ASR_MODEL = "paraformer-realtime-v2"   # 中文/多语种实时模型
SAMPLE_RATE = 16000                    # Paraformer 要求 16k

# ---- 热词 / 偏置（把 VOCAB 喂给 ASR 本身，让名字/术语一开始就听对）----
# 云端：用 VOCAB 建 Paraformer 热词表(vocabulary_id)；本地：拼成 Whisper initial_prompt。
# 一份 VOCAB，两处生效。VOCAB 为空时本功能自动不启用、零副作用。
HOTWORDS_ENABLED = True
HOTWORD_WEIGHT = 4                     # 热词权重 1-5，越大偏置越强
HOTWORD_PREFIX = "vi"                  # 热词表前缀（仅小写字母+数字，<10 字符）

# ---- 本地 Whisper (ASR_BACKEND="local" 时生效) ----
# 模型越大越准越慢。tiny/base/small 快，large-v3-turbo 准。首次用会自动下载。
LOCAL_ASR_MODEL = "mlx-community/whisper-large-v3-turbo"
LOCAL_ASR_LANGUAGE = "zh"
CHANNELS = 1
DTYPE = "int16"                        # 16-bit PCM
BLOCK_MS = 200                         # 每帧 200ms
BLOCK_SIZE = SAMPLE_RATE * BLOCK_MS // 1000

# ---- 语义清洗后端选择 ----
# "deepseek" = DeepSeek 云端（默认，中文强、极便宜，需 key）
# "ollama"   = 本地 Ollama（离线、免费、免 key；需自行安装 Ollama 并拉模型）
POLISH_BACKEND = "deepseek"

# ---- DeepSeek 语义清洗 ----
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# ---- 本地 Ollama (POLISH_BACKEND="ollama" 时生效，OpenAI 兼容接口) ----
# 先装 Ollama 并 `ollama pull qwen2.5`，它会在 localhost:11434 提供服务。
OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_MODEL = "qwen2.5"

POLISH_ENABLED = True                  # 菜单栏可临时开关
POLISH_TIMEOUT = 8                     # 秒；超时就退回原始转写，保证不卡

# 专属词汇表：人名、术语、产品名等。列在这里的词，清洗时会原样保留，
# 不会被当作同音字"纠正"。例如把同事名字、公司黑话、专有名词加进来。
VOCAB = [
    # "张伟", "语忆", "Paraformer", "DeepSeek",
]

# 清洗风格：菜单栏可切换。key 是菜单里显示的名字，value 是对应的系统提示。
POLISH_STYLES = {
    "书面": """你是语音输入的文本整理助手。用户的话是语音转写来的口语，可能有口头禅、重复、同音字错误、缺标点。
请整理成简洁、通顺、可直接使用的【书面中文】：
- 去掉「嗯、那个、就是说、然后呢」之类口头禅和无意义重复
- 修正明显的同音字/转写错误（结合上下文判断）
- 补全标点、合理断句分段
- 若口述里有明确格式指令（如"分点列出""换行"），按指令执行""",

    "口语": """你是语音输入的文本整理助手。用户的话是语音转写来的口语。
请做【轻度整理】，保留口语、自然的说话风格，不要改写成书面正式语气：
- 只去掉明显的卡顿、重复和「嗯、呃」这类语气填充
- 修正同音字/转写错误，补上必要标点
- 用词、句式、语气尽量保持用户原样""",

    "邮件": """你是语音输入的文本整理助手。用户在口述一封邮件的内容。
请把它整理成一段【礼貌、得体、条理清晰的中文邮件正文】：
- 去掉口语口头禅和重复，组织成通顺的书面表达
- 语气专业友好，必要时分段
- 只输出邮件正文，不要自行加收件人称呼或落款署名（除非用户口述里明确说了）""",
}
POLISH_STYLE = "书面"   # 默认风格，菜单可切换

_COMMON_RULE = """\n严格要求：只输出整理后的正文本身，不要任何解释、前后缀、引号或"以下是"之类的话。保持用户原意，不要增删信息、不要扩写。"""


def build_polish_prompt(style: str = None, extra_vocab=None) -> str:
    """根据风格 + 词汇表，拼出完整的系统提示（每次清洗时调用，支持运行时切换）。
    style 为空时用当前菜单选的 POLISH_STYLE；extra_vocab 为 app 专属补充词汇。"""
    name = style or POLISH_STYLE
    prompt = POLISH_STYLES.get(name, POLISH_STYLES["书面"])
    vocab = [w for w in list(VOCAB) + list(extra_vocab or []) if w and w.strip()]
    if vocab:
        prompt += (
            "\n以下是用户的专有名词/人名/术语：" + "、".join(vocab)
            + "。请原样保留它们；并且——如果转写文本里出现这些词的明显错听或音译版本"
            "（发音相近即可，尤其中英文混说时被听错的英文词，如把 Typeless 听成 checplace），"
            "请还原成上面列表里的正确写法。"
        )
    return prompt + _COMMON_RULE


# ---- 上下文感知 ----
CONTEXT_ENABLED = True          # 菜单栏可开关；只在「语义清洗」开着时生效
PRECEDING_CHARS = 300           # 读光标前最多这么多字当上下文
HISTORY_SIZE = 3                # 记住最近几次口述
HISTORY_WINDOW_SEC = 180        # 且只算最近这么多秒内的（超时的不再当上下文）

# 按前台 app 自动套用风格/补充词汇。key 是 app 的 bundle id。
# 默认空（不打扰，风格仍由菜单手动选）。想用就照例子填：
# APP_PROFILES = {
#     "com.apple.mail":     {"style": "邮件"},
#     "com.tencent.xinWeChat": {"style": "口语"},
#     "com.microsoft.VSCode": {"vocab": ["async", "await", "repo"]},
# }
APP_PROFILES = {}

# ---- 热键 ----
# 按住说话(hold-to-talk)。用 macOS 键码(keycode)匹配，最稳，不受 pynput 枚举名差异影响。
# 常见键码: 左Option=58 右Option=61 | 左Cmd=55 右Cmd=54 | 左Ctrl=59 右Ctrl=62 | CapsLock=57
# 注意: fn(地球仪)键 pynput 抓不到，不能用。
# 默认: 左右 Option 任意一个都触发。想换成右 Cmd 就写 {54}，右 Ctrl 写 {62}。
HOTKEY_KEYCODES = {58, 61}
HOTKEY_NAME = "Option"
