"""把 VOCAB 喂给 ASR 本身做偏置，让名字/术语在识别第一步就听对。

- 云端 Paraformer：用 VOCAB 建热词表，拿到 vocabulary_id 传给识别。热词表按
  VOCAB 内容哈希缓存到磁盘，内容没变就不重建（不每次启动都调 API）。
- 本地 Whisper：把 VOCAB 拼成 initial_prompt 偏置解码。

VOCAB 为空 / 关闭开关时，全部静默跳过，零副作用、零网络调用。

English: Bias the ASR toward your VOCAB so names/terms are recognized correctly
from the start. Cloud → Paraformer hot-word vocabulary; local → Whisper initial_prompt.
"""
import hashlib
import json
import os
import threading

import config

_SUPPORT = os.path.expanduser("~/Library/Application Support/voiceinput")
_CACHE = os.path.join(_SUPPORT, "paraformer_vocab.json")

_vocab_id = None          # 已就绪的 Paraformer vocabulary_id（None=无）
_lock = threading.Lock()


def _items():
    return [w.strip() for w in config.VOCAB if w and w.strip()]


def _hash(items, model):
    key = model + "|" + "\n".join(sorted(items))
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


# ---------- 本地 Whisper ----------
def whisper_initial_prompt():
    """把 VOCAB 拼成偏置用的 initial_prompt；无词则 None。"""
    if not config.HOTWORDS_ENABLED:
        return None
    items = _items()
    if not items:
        return None
    return "可能出现的专有名词与术语：" + "、".join(items) + "。"


# ---------- 云端 Paraformer ----------
def get_paraformer_vocabulary_id():
    """返回已就绪的 vocabulary_id（后台还没建好时为 None，识别照常进行）。"""
    with _lock:
        return _vocab_id


def _load_cache():
    try:
        with open(_CACHE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(d):
    try:
        os.makedirs(_SUPPORT, exist_ok=True)
        with open(_CACHE, "w") as f:
            json.dump(d, f, ensure_ascii=False)
    except Exception:
        pass


def prepare_async():
    """app 启动时调用：确保 Paraformer 热词表就绪。
    命中磁盘缓存就直接用（无网络）；VOCAB 变了才后台重建。"""
    global _vocab_id
    if (config.ASR_BACKEND != "paraformer" or not config.HOTWORDS_ENABLED
            or not config.DASHSCOPE_API_KEY):
        return
    items = _items()
    if not items:
        return

    h = _hash(items, config.ASR_MODEL)
    cache = _load_cache()
    if cache.get("hash") == h and cache.get("vocabulary_id"):
        with _lock:
            _vocab_id = cache["vocabulary_id"]
        return

    def _work():
        global _vocab_id
        try:
            import dashscope
            from dashscope.audio.asr import VocabularyService
            dashscope.api_key = config.DASHSCOPE_API_KEY
            svc = VocabularyService()
            # 先删旧的，避免账号里堆积无用热词表
            old = _load_cache().get("vocabulary_id")
            if old:
                try:
                    svc.delete_vocabulary(old)
                except Exception:
                    pass
            vocab = [{"text": w, "weight": config.HOTWORD_WEIGHT, "lang": "zh"}
                     for w in items]
            vid = svc.create_vocabulary(
                target_model=config.ASR_MODEL,
                prefix=config.HOTWORD_PREFIX,
                vocabulary=vocab,
            )
            with _lock:
                _vocab_id = vid
            _save_cache({"hash": h, "vocabulary_id": vid})
            print(f"[热词] Paraformer 热词表就绪（{len(items)} 词）vocabulary_id={vid}")
        except Exception as e:
            print(f"[热词] 创建失败，忽略、照常识别：{e}")

    threading.Thread(target=_work, daemon=True).start()
