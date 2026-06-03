import anthropic

from app.core.config import get_settings
from app.core.exceptions import LLMProviderError
from app.core.logging import get_logger
from app.schemas.llm import LLMGenerateRequest, LLMGenerateResponse, LLMProvider
from app.services.llm.base import BaseLLMService

logger = get_logger(__name__)
settings = get_settings()


class ClaudeService(BaseLLMService):
    provider_name = "claude"
    default_model = "claude-3-5-haiku-20241022"

    def __init__(self) -> None:
        if not settings.ANTHROPIC_API_KEY:
            raise LLMProviderError("claude", "ANTHROPIC_API_KEY is not configured.")
        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def generate(self, request: LLMGenerateRequest) -> LLMGenerateResponse:
        model_name = self._resolve_model(request.model)
        kwargs: dict = dict(
            model=model_name,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            messages=[{"role": "user", "content": request.prompt}],
        )
        if request.system_prompt:
            kwargs["system"] = request.system_prompt

        try:
            response = await self._client.messages.create(**kwargs)
            text = "".join(
                block.text for block in response.content if hasattr(block, "text")
            )
            return LLMGenerateResponse(
                text=text,
                provider=LLMProvider.CLAUDE,
                model=model_name,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                finish_reason=response.stop_reason,
            )
        except Exception as exc:
            logger.exception("Claude generation failed")
            raise LLMProviderError("claude", str(exc)) from exc

    async def health_check(self) -> bool:
        try:
            await self._client.messages.create(
                model=self.default_model,
                max_tokens=5,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception:
            return False
