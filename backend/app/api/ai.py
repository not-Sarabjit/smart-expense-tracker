from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies.auth import get_current_user  
from app.models.user import User 
from app.ai.rag.retriever import answer_question, RAGResponse
from app.ai.rag.ingestion import ingest_transactions
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.category_repository import CategoryRepository  
from app.schemas.ai import AskRequest, AskResponse, IngestResponse 
from app.database.session import get_db 

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/ask", response_model=AskResponse)
def ask(
    request: AskRequest,
    current_user: User = Depends(get_current_user),
) -> AskResponse:
    """
    Ask a natural-language question about your own transaction data.
    Answer is grounded in retrieved chunks — see source_documents.
    """
    result: RAGResponse = answer_question(
        user_id=str(current_user.id),
        question=request.question,
    )

    return AskResponse(
        answer=result.answer,
        source_documents=result.source_documents,
        tokens_used=result.tokens_used,
    )


@router.post("/ingest-transactions", response_model=IngestResponse)
def ingest_transactions_endpoint(
    current_user: User = Depends(get_current_user),
    db:Session =  Depends(get_db),
) -> IngestResponse:
    """
    (Re)ingests the current user's transactions into the vector store so
    they become searchable via /ai/ask. Call this after bulk imports or
    periodically to keep the index fresh.
    """
    transaction_repo = TransactionRepository(db)  # adjust to however you inject repos
    category_repo =  CategoryRepository(db)  
    chunks_written = ingest_transactions(
        user_id=str(current_user.id),
        transaction_repo=transaction_repo,
        category_repo=category_repo
    )

    return IngestResponse(chunks_ingested=chunks_written)