"""Production chat LLM client boundary."""

from __future__ import annotations

from typing import Any, Optional, Protocol

from pydantic import SecretStr
from langchain_openai import ChatOpenAI

from app.core.config import settings


class ChatLLMProviderError(Exception):
    """Raised when the chat LLM provider is unavailable or returns unusable output."""


class ChatLLMClientProtocol(Protocol):
    async def generate_reply(self, *, user_message: str, working_memory: str) -> str:
        ...


class OpenAIChatLLMClient(ChatLLMClientProtocol):
    """Production chat completion client using OpenAI/LangChain."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[SecretStr] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self.model_name = model_name or settings.OPENAI_MODEL
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.base_url = base_url or settings.OPENAI_LLM_BASE_URL or settings.OPENAI_BASE_URL
        self._llm: Any | None = None

    def _get_llm(self) -> Any:
        if self._llm is None:
            api_key = self.api_key.get_secret_value() if self.api_key else ""
            if not api_key or api_key == "your-openai-api-key":
                raise ChatLLMProviderError("Valid OPENAI_API_KEY is not configured.")
            try:
                self._llm = ChatOpenAI(
                    model=self.model_name,
                    api_key=api_key,
                    base_url=self.base_url or None,
                    temperature=0.2,
                )
            except Exception as exc:
                raise ChatLLMProviderError("Failed to initialize chat LLM.") from exc
        return self._llm

    async def generate_reply(self, *, user_message: str, working_memory: str) -> str:
        prompt = build_chat_prompt(user_message=user_message, working_memory=working_memory)
        try:
            response = await self._get_llm().ainvoke(prompt)
        except ChatLLMProviderError:
            raise
        except Exception as exc:
            raise ChatLLMProviderError("Chat LLM provider call failed.") from exc

        content = _message_content(response)
        if not content.strip():
            raise ChatLLMProviderError("Chat LLM returned an empty response.")
        return content.strip()


def build_chat_prompt(*, user_message: str, working_memory: str) -> str:
    return (
        "You are an AI Job Agent inside a user's job-search workspace.\n"
        "Use the provided working memory as your only source for saved profile, "
        "conversation, job, and application facts.\n"
        "Do not invent job listings, scores, profile facts, URLs, or application statuses.\n"
        "If the user asks for an action that requires a tool that has not run yet, "
        "say exactly what action/tool is needed next.\n"
        "Keep answers direct and useful.\n\n"
        f"Working memory:\n{working_memory}\n\n"
        f"User message:\n{user_message}"
    )


def _message_content(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts)
    return str(content)
