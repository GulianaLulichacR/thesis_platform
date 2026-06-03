from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.exceptions import LLMProviderError
from app.core.logging import get_logger
from app.schemas.llm import LLMGenerateRequest, LLMGenerateResponse, LLMProvider
from app.services.llm.base import BaseLLMService

logger = get_logger(__name__)
settings = get_settings()


class OpenAIService(BaseLLMService):
    provider_name = "openai"
    default_model = "gpt-4o-mini"

    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY:
            raise LLMProviderError("openai", "OPENAI_API_KEY is not configured.")
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def generate(self, request: LLMGenerateRequest) -> LLMGenerateResponse:
        model_name = self._resolve_model(request.model)
        messages = self._build_messages(request.prompt, request.system_prompt)
        try:
            response = await self._client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
            choice = response.choices[0]
            return LLMGenerateResponse(
                text=choice.message.content or "",
                provider=LLMProvider.OPENAI,
                model=model_name,
                input_tokens=response.usage.prompt_tokens if response.usage else None,
                output_tokens=response.usage.completion_tokens if response.usage else None,
                finish_reason=choice.finish_reason,
            )
        except Exception as exc:
            logger.exception("OpenAI generation failed")
            raise LLMProviderError("openai", str(exc)) from exc

    async def health_check(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False
