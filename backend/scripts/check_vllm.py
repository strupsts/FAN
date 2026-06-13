from __future__ import annotations

import json
import urllib.error
import urllib.request

from app.infrastructure.config import get_settings


def main() -> None:
    settings = get_settings()
    url = settings.vllm_base_url.rstrip("/") + "/models"

    request = urllib.request.Request(
        url=url,
        headers={
            "Authorization": f"Bearer {settings.vllm_api_key}",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=settings.vllm_timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except urllib.error.URLError as error:
        raise SystemExit(
            "vLLM is not available.\n"
            f"Tried: {url}\n"
            f"Error: {error}\n\n"
            "Start vLLM first, then retry: make llm-health"
        ) from error

    data = json.loads(body)

    print("vLLM is available.")
    print(f"Base URL: {settings.vllm_base_url}")
    print("Models:")

    for model in data.get("data", []):
        print(f"- {model.get('id')}")


if __name__ == "__main__":
    main()
