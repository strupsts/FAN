from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
import time

import requests


@dataclass
class LLMCoreConfig:
    host: str = "http://127.0.0.1:8000"   # vLLM
    model: str = "qwen3-8b"               # served-model-name
    timeout_s: int = 120                  # было 60
    num_predict_default: int = 256


class LLMCore:
    def __init__(self, config: Optional[LLMCoreConfig] = None) -> None:
        self.config = config or LLMCoreConfig()
        self._session = requests.Session()  # keep-alive + меньше оверхеда

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        no_think: bool = False,
        format: Optional[Union[str, Dict[str, Any]]] = None,  # пока не используем
        return_meta: bool = False,
        extra_options: Optional[Dict[str, Any]] = None,
        debug_raw: bool = False,
    ) -> Union[str, Tuple[str, Dict[str, Any]]]:
        msgs = [dict(m) for m in messages]

        if no_think:
            for m in reversed(msgs):
                if m.get("role") == "user":
                    c = m.get("content", "")
                    if "/no_think" not in c:
                        m["content"] = c.rstrip() + "\n/no_think"
                    break

        num_predict = int(max_tokens or self.config.num_predict_default)

        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": msgs,
            "temperature": float(temperature),
            "max_tokens": num_predict,
            "stream": False,
        }
        if extra_options:
            payload.update(extra_options)

        t0 = time.time()

        # 1 retry на ReadTimeout
        last_exc: Exception | None = None
        for attempt in (1, 2):
            try:
                resp = self._session.post(
                    f"{self.config.host}/v1/chat/completions",
                    json=payload,
                    timeout=(5, self.config.timeout_s),  # connect, read
                )
                resp.raise_for_status()
                data = resp.json()
                break
            except requests.exceptions.ReadTimeout as e:
                last_exc = e
                if attempt == 2:
                    raise
            except Exception as e:
                last_exc = e
                raise

        choice0 = (data.get("choices") or [{}])[0]
        content_raw = ((choice0.get("message") or {}).get("content")) or ""
        if debug_raw:
            print("\n[LLM RAW content_raw repr]", repr(content_raw), flush=True)

        content = content_raw.strip()

        if not return_meta:
            return content

        meta: Dict[str, Any] = {}
        meta["wall_s"] = time.time() - t0
        meta["finish_reason"] = choice0.get("finish_reason")
        meta["usage"] = data.get("usage", {})

        try:
            out_tok = float(meta["usage"].get("completion_tokens", 0))
            meta["tok_per_s_out"] = out_tok / meta["wall_s"] if meta["wall_s"] > 0 else None
        except Exception:
            meta["tok_per_s_out"] = None

        return content, meta
