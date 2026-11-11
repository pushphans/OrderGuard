from langchain_groq import ChatGroq

from orderguard_ai.core.config import settings

DEFAULT_LLM_MODEL = "llama-3.3-70b-versatile"


def get_llm(
    model: str = DEFAULT_LLM_MODEL,
    temperature: float = 0.1,
) -> ChatGroq:
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY environment variable is not set")

    return ChatGroq(model=model, temperature=temperature, api_key=settings.GROQ_API_KEY)
