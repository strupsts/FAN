from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",  # просто заглушка, Ollama не проверяет
)

prompt = """
You are a JSON-only classifier for shopping items.

Input:
merchant: Walmart
item_name: Milk 2L
price: 3.99
lang: en

Return JSON with fields:
- category: one of [DAIRY, MEAT, VEGETABLES, FASTFOOD, COFFEE, PHARMACY, AUTO, BAKERY, ELECTRONICS, HOUSEHOLD, TAKEOUT, WANTS_OTHER]
- bucket: one of [NEEDS, WANTS]
- confidence: float 0..1
- norm_name: short normalized English name of the item

Return ONLY JSON, no text around it.
"""

resp = client.chat.completions.create(
    model="qwen3:8b",
    temperature=0.1,
    messages=[
        {"role": "system", "content": "You are a strict JSON API."},
        {"role": "user", "content": prompt},
    ],
)

print(resp.choices[0].message.content)
