from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.ai.vector_store import get_vector_store
from app.repositories.transaction_repository import TransactionRepository  
from app.repositories.category_repository import CategoryRepository  



CHUNK_SIZE = 512
CHUNK_OVERLAP = 64

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
)


def ingest_documents(docs: list[Document], user_id: str) -> int:
    """
    Splits and ingests a list of Documents into Qdrant, tagging every
    resulting chunk with user_id in the metadata payload. This metadata
    is what retrieval (2.5) filters on for multi-tenancy.

    Returns the number of chunks written.
    """
    if not docs:
        return 0

    # Adding user id to each doc in meta data for filtering
    for doc in docs:
        doc.metadata["user_id"] = user_id

    chunks = _splitter.split_documents(docs)

    vector_store = get_vector_store()
    vector_store.add_documents(chunks)

    return len(chunks)


def ingest_transactions(user_id: str, transaction_repo: TransactionRepository, category_repo: CategoryRepository) -> int:
    """
    Pulls all of a user's transactions from the DB, converts each into a
    Document (so it can be embedded and searched), and ingests them.
    """
    transactions = transaction_repo.get_all_for_user(user_id)  

    docs: list[Document] = []
    for txn in transactions:
        category = category_repo.get_by_id(txn.category_id)
        category = 'None' if not category else category.name

        content = (
            f"On {txn.date}, spent {txn.amount} on {category} "
            f"Note: {txn.description or 'no description'}."
        )
        docs.append(
            Document(
                page_content=content,
                metadata={
                    "user_id": user_id,
                    "transaction_id": str(txn.id),
                    "category": category,
                    "date": str(txn.date),
                },
            )
        )

    return ingest_documents(docs, user_id)