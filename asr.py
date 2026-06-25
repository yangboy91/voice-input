"""阿里云 Paraformer 流式语音识别封装。

用法：
    session = ParaformerSession()
    session.start()
    session.feed(pcm_bytes)   # 在录音过程中不断喂 16k/16bit/mono 的 PCM
    ...
    text = session.stop()     # 返回最终整段文本
"""
import config  # 必须先导入：它在顶部给 ssl 打了 certifi 补丁，要早于 dashscope/aiohttp

import dashscope
from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult

dashscope.api_key = config.DASHSCOPE_API_KEY


def _safe(result, attr):
    """安全读取 SDK 结果对象的属性（它的 __getattr__ 对未知属性会抛错）。"""
    try:
        return getattr(result, attr, None)
    except Exception:
        return None


class _Collector(RecognitionCallback):
    """收集流式返回的句子，并安全捕获错误。"""

    def __init__(self):
        self.finalized = []   # 已确定的句子
        self.partial = ""     # 当前未结束的句子
        self.error = None     # 服务端错误信息（如有）
        self.running = True

    def on_close(self):
        self.running = False

    def on_complete(self):
        self.running = False

    def on_error(self, result):
        self.running = False
        # 不要用 str(result)：SDK 的 __str__ 有 headers 的 bug，会把真实信息吞掉
        code = _safe(result, "status_code") or _safe(result, "code")
        msg = _safe(result, "message")
        out = _safe(result, "output")
        self.error = f"code={code} | message={msg} | output={out}"
        print(f"[ASR错误] {self.error}")

    def on_event(self, result: RecognitionResult):
        sentence = result.get_sentence()
        if not sentence:
            return
        # realtime-v2 可能返回单个 dict，也可能返回 dict 列表
        sentences = sentence if isinstance(sentence, list) else [sentence]
        for s in sentences:
            if not isinstance(s, dict):
                continue
            text = s.get("text", "")
            if not text:
                continue
            if RecognitionResult.is_sentence_end(s):
                self.finalized.append(text)
                self.partial = ""
            else:
                self.partial = text

    def full_text(self) -> str:
        return "".join(self.finalized) + self.partial


class ParaformerSession:
    def __init__(self):
        self._collector = None
        self._recognition = None
        self.last_error = None

    def start(self):
        self._collector = _Collector()
        self._recognition = Recognition(
            model=config.ASR_MODEL,
            format="pcm",
            sample_rate=config.SAMPLE_RATE,
            callback=self._collector,
        )
        self._recognition.start()

    def feed(self, pcm_bytes: bytes):
        # 会话已被服务端关闭/出错后，不再喂，避免 send_audio_frame 抛 "has stopped"
        if self._recognition is None or self._collector is None:
            return
        if not self._collector.running:
            return
        try:
            self._recognition.send_audio_frame(pcm_bytes)
        except Exception:
            self._collector.running = False

    def stop(self) -> str:
        if self._recognition is None:
            return ""
        try:
            self._recognition.stop()
        except Exception:
            pass
        text = self._collector.full_text().strip()
        self.last_error = self._collector.error
        self._recognition = None
        self._collector = None
        return text
