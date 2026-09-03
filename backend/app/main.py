from app.ai.client import ai_client

# Plain text response
response = ai_client.complete(
    prompt="How to spend 100 $ in short",
    system="You are a financial assistant."
)

# Structured JSON response
data = ai_client.complete_json(
    prompt='Extract the amount from: "paid 340 for groceries". Return {"amount": float, "description": str}'
)
print(data) 

print(response)