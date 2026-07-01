from typing import Any
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from app.services.chat_llm_client import (
    ChatLLMProviderError,
    OpenAIChatLLMClient,
    build_chat_prompt,
)


class _ChatMessage:
    content = "  Use your profile to compare saved roles.  "


class _ChatLLMDouble:
    def __init__(self) -> None:
        self.prompts: list[Any] = []

    async def ainvoke(self, prompt: Any) -> _ChatMessage:
        self.prompts.append(prompt)
        return _ChatMessage()


def test_build_chat_prompt_includes_memory_and_user_message() -> None:
    prompt = build_chat_prompt(
        user_message="What skills am I missing?",
        working_memory="Profile skills: Python, SQL",
    )

    assert "Do not invent job listings" in prompt
    assert "Profile skills: Python, SQL" in prompt
    assert "What skills am I missing?" in prompt


def test_chat_client_passes_configured_base_url() -> None:
    with patch("app.services.chat_llm_client.ChatOpenAI") as chat_openai:
        client = OpenAIChatLLMClient(
            model_name="test-model",
            api_key=SecretStr("test-api-key"),
            base_url="https://llm-gateway.test/v1",
        )
        client._get_llm()

    chat_openai.assert_called_once_with(
        model="test-model",
        api_key="test-api-key",
        base_url="https://llm-gateway.test/v1",
        temperature=0.2,
    )


@pytest.mark.asyncio
async def test_chat_client_raises_provider_error_on_missing_key() -> None:
    client = OpenAIChatLLMClient(api_key=SecretStr("your-openai-api-key"))

    with pytest.raises(ChatLLMProviderError, match="Valid OPENAI_API_KEY is not configured"):
        await client.generate_reply(
            user_message="Find jobs",
            working_memory="Profile: AI Engineer",
        )


@pytest.mark.asyncio
async def test_chat_client_invokes_llm_with_prompt_text() -> None:
    llm = _ChatLLMDouble()
    client = OpenAIChatLLMClient(
        model_name="test-model",
        api_key=SecretStr("test-api-key"),
    )
    client._llm = llm

    answer = await client.generate_reply(
        user_message="Compare this job with my profile",
        working_memory="Profile: Backend engineer",
    )

    assert answer == "Use your profile to compare saved roles."
    assert llm.prompts
    assert "Compare this job with my profile" in llm.prompts[0]
