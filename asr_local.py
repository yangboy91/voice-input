"""本地语音识别后端（mlx-whisper，Apple Silicon 原生）。

与 asr.ParaformerSession 同接口（start/feed/stop），可被 app 透明替换。
属可选功能：mlx-whisper 是可选依赖（requirements-local.txt），默认不打包进 .app。
录音时缓冲 PCM，松开时一次性本地转写——无需联网、无需 API key。

English: Optional local ASR backend using mlx-whisper (Apple Silicon).
Same interface as the cloud Paraformer session, selected via config.ASR_BACKEND.
"""
import config


class LocalWhisperSession:
    def __init__(self):
        self._chunks = []
        self.last_error = None

    def start(self):
        self._chunks = []
        self.last_error = None

    def feed(self, pcm_bytes: bytes):
        # 本地后端不流式，先把 16k/16bit/mono PCM 缓存起来
        if pcm_bytes:
            self._chunks.append(pcm_bytes)

    def stop(self) -> str:
        if not self._chunks:
            return ""
        try:
            import numpy as np
            import mlx_whisper
        except ImportError:
            self.last_error = (
                "本地 Whisper 未安装。请: pip install -r requirements-local.txt"
            )
            print(f"[asr_local] {self.last_error}")
            return ""

        pcm = b"".join(self._chunks)
        self._chunks = []
        # int16 PCM → float32 [-1,1]，mlx-whisper 直接吃 numpy 数组（绕开 ffmpeg）
        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        try:
            result = mlx_whisper.transcribe(
                audio,
                path_or_hf_repo=config.LOCAL_ASR_MODEL,
                language=config.LOCAL_ASR_LANGUAGE,
            )
            return (result.get("text") or "").strip()
        except Exception as e:
            self.last_error = str(e)
            print(f"[asr_local] 转写失败: {e}")
            return ""
