import os

from dotenv import load_dotenv
from ollama import Client

load_dotenv()

api_key = os.environ.get("OLLAMA_API")
if not api_key:
    raise SystemExit("OLLAMA_API не найден в .env")

client = Client(
    host="https://ollama.com",
    headers={"Authorization": f"Bearer {api_key}"},
)

response = client.chat(
    model="glm-5.2:cloud",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Why is the sky blue?"},
    ],
    stream=False,
    options={"num_predict": 100, "temperature": 0},
)

print(response)