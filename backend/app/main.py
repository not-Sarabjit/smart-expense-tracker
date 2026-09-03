# paste in a Python shell or a temp script, then delete
from openai import OpenAI

client = OpenAI(
    api_key="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",
    base_url="https://api.groq.com/openai/v1",
)

models = client.models.list()

for model in models.data:
    print(model.id)

resp = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[{"role": "user", "content": "What is up"}]
)
print(resp.choices[0].message.content)
# Expected: "Hello!" or similar