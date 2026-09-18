from pydantic import BaseModel
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain

from app.ai.llm import get_llm
from app.ai.vector_store import get_vector_store


class RAGResponse(BaseModel):
    answer: str
    source_documents: list[dict]
    tokens_used: int | None = None


_RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful financial assistant. Answer the user's question "
            "using ONLY the transaction context below. If the context doesn't "
            "contain enough information to answer, say so honestly — do not "
            "guess or make up numbers.\n\nContext:\n{context}",
        ),
        ("human", "{input}"),
    ]
)


def _build_chain(user_id: str):
    """
    Builds a per-request retrieval chain scoped to a single user.
    The filter here is the multi-tenancy guard — it must never be omitted.
    """
    vector_store = get_vector_store()

    retriever = vector_store.as_retriever(
        search_kwargs={
            "k": 6,
            "filter": {"user_id": user_id},
        }
    )

    document_chain = create_stuff_documents_chain(get_llm(), _RAG_PROMPT)
    return create_retrieval_chain(retriever, document_chain)


def answer_question(user_id: str, question: str) -> RAGResponse:
    """
    Runs the RAG pipeline for a single question, scoped to user_id.
    """
    chain = _build_chain(user_id)
    result = chain.invoke({"input": question})

    source_docs: list[Document] = result.get("context", [])

    return RAGResponse(
        answer=result["answer"],
        source_documents=[
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
            }
            for doc in source_docs
        ],
    )