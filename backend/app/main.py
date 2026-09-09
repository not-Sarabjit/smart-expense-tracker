
from app.core.config import settings

print(settings.GROQ_MODEL)        # llama-3.3-70b-versatile
print(settings.QDRANT_URL)        # http://localhost:6333
print(settings.QDRANT_COLLECTION) # expense_docs
print("Config loaded successfully ✓")