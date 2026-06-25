"""用 DeepSeek 把口语转写清洗成干净书面文本。

DeepSeek 提供 OpenAI 兼容接口，直接用 openai SDK 指向其 base_url 即可。
任何失败/超时都回退到原始文本，保证不影响输入。
"""
from openai import OpenAI

import config

_client = OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
    timeout=config.POLISH_TIMEOUT,
)


def polish(raw_text, preceding_text=None, recent=None, style=None, extra_vocab=None):
    """清洗本次口述。可选上下文（光标前文字、最近口述）会一并喂给模型帮助
    自然衔接、统一术语——但全部塞进这一次调用，不增加额外往返。"""
    raw_text = raw_text.strip()
    if not raw_text:
        return ""

    system = config.build_polish_prompt(style=style, extra_vocab=extra_vocab)

    parts = []
    has_ctx = False
    if preceding_text:
        parts.append("【光标前已有的文字（仅供理解上下文，绝不要重复或包含它）】\n" + preceding_text)
        has_ctx = True
    if recent:
        joined = "\n".join(t[:200] for t in recent if t)
        if joined:
            parts.append("【我最近几次的口述（仅供统一术语/语气）】\n" + joined)
            has_ctx = True
    parts.append("【需要整理的本次口述】\n" + raw_text)
    user = "\n\n".join(parts)

    if has_ctx:
        system += (
            "\n注意：用户可能附带【光标前已有的文字】和【最近的口述】作为上下文，"
            "只为帮你自然衔接上文、统一术语；你只需输出对【需要整理的本次口述】的整理结果，"
            "让它能顺畅接在光标前文字之后，但绝不要重复或包含任何上下文内容。"
        )

    try:
        resp = _client.chat.completions.create(
            model=config.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=2048,
        )
        cleaned = resp.choices[0].message.content.strip()
        return cleaned or raw_text
    except Exception as e:
        print(f"[polish] DeepSeek 清洗失败，回退原始文本: {e}")
        return raw_text
