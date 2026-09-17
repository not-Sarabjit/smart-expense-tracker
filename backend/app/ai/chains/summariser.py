from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.ai.llm import get_llm

SUMMARISE_PROMPT = PromptTemplate(
    input_variables=["text"],
    template=(
        "You are a concise financial assistant. "
        "Summarise the following text in 2-3 sentences. "
        "Focus on the key financial facts.\n\n"
        "Text:\n{text}\n\n"
        "Summary:"
    ),
)


def get_summariser_chain():
    """
    Build and return the summariser LCEL chain.
    Chain: PromptTemplate | ChatGroq | StrOutputParser
    This is the canonical LCEL pipe pattern used throughout the app.
    """
    llm = get_llm()
    chain = SUMMARISE_PROMPT | llm | StrOutputParser()
    return chain


def summarise_text(text: str) -> str:
    """
    Summarise the given text using the Groq LLM.

    Args:
        text: The text to summarise.

    Returns:
        A concise 2-3 sentence summary string.
    """
    chain = get_summariser_chain()
    return chain.invoke({"text": text})


async def summarise_text_async(text: str) -> str:
    """
    Async version of summarise_text. Use in async FastAPI endpoints.
    """
    chain = get_summariser_chain()
    return await chain.ainvoke({"text": text})