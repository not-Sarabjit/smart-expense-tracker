from app.ai.llm import get_llm




llm = get_llm()
response = llm.invoke("Give me python code to reverse a list without using inbuilt")
print(response.content)   # Should print something like: "Hello!"
print("LLM factory working ✓")