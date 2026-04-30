import os
from typing import AsyncIterator
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

SYSTEM_PROMPT = """You are Harvey, an AI legal assistant. You help lawyers and legal professionals with:
- Document analysis and review
- Contract drafting and review
- Legal research
- Summarizing legal documents
- Identifying key clauses, risks, and obligations

Be precise, thorough, and cite specific sections when referencing documents.
Always note when something requires human legal judgment."""

AVAILABLE_MODELS = {
    "OpenAI": {
        "gpt-4o": "GPT-4o",
        "gpt-4o-mini": "GPT-4o Mini",
        "gpt-4.1": "GPT-4.1",
        "gpt-4.1-mini": "GPT-4.1 Mini",
        "gpt-4.1-nano": "GPT-4.1 Nano",
        "o4-mini": "o4-mini",
    },
    "Anthropic": {
        "claude-sonnet-4-6": "Claude Sonnet 4.6",
        "claude-haiku-4-5": "Claude Haiku 4.5",
    },
    "Google": {
        "gemini-2.5-flash": "Gemini 2.5 Flash",
        "gemini-2.5-pro": "Gemini 2.5 Pro",
    },
}

def _provider_for_model(model_id: str) -> str:
    if model_id.startswith("gpt") or model_id.startswith("o4") or model_id.startswith("o3"):
        return "openai"
    if model_id.startswith("claude"):
        return "anthropic"
    if model_id.startswith("gemini"):
        return "google"
    return "openai"

def get_chat_model(model_id: str | None = None, streaming: bool = True):
    model_id = model_id or os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
    provider = _provider_for_model(model_id)

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model_id, streaming=streaming)
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model_id, streaming=streaming)
    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model_id, streaming=streaming)
    else:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model_id, streaming=streaming)

def build_messages(history: list[dict], system_prompt: str | None = None):
    msgs = [SystemMessage(content=system_prompt or SYSTEM_PROMPT)]
    for m in history:
        if m["role"] == "user":
            msgs.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            msgs.append(AIMessage(content=m["content"]))
    return msgs

async def stream_chat(history: list[dict], model_id: str | None = None, system_prompt: str | None = None) -> AsyncIterator[str]:
    llm = get_chat_model(model_id, streaming=True)
    msgs = build_messages(history, system_prompt)
    async for chunk in llm.astream(msgs):
        if chunk.content:
            yield chunk.content

async def generate_response(history: list[dict], model_id: str | None = None, system_prompt: str | None = None) -> str:
    llm = get_chat_model(model_id, streaming=False)
    msgs = build_messages(history, system_prompt)
    resp = await llm.ainvoke(msgs)
    return resp.content

async def generate_title(message: str, model_id: str | None = None) -> str:
    llm = get_chat_model(model_id or "gpt-4o-mini", streaming=False)
    msgs = [
        SystemMessage(content="Generate a short title (max 6 words) for this conversation. Return only the title, no quotes."),
        HumanMessage(content=message),
    ]
    resp = await llm.ainvoke(msgs)
    return resp.content.strip().strip('"\'')
