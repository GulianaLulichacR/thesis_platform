from fastapi import APIRouter, status

from app.core.logging import get_logger
from app.schemas.llm import ChatRequest, ChatResponse, LLMGenerateRequest
from app.services.llm.fallback_engine import get_fallback_engine
from app.services.storage.local_storage import LocalStorageService
from app.services.document.pdf_loader import PDFLoader
from app.services.document.docx_loader import DOCXLoader
from app.core.exceptions import StorageError

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = get_logger(__name__)

_storage = LocalStorageService()
_pdf_loader = PDFLoader()
_docx_loader = DOCXLoader()

THESIS_SYSTEM_PROMPT = """You are an expert academic thesis reviewer.
You have been given the full text of a student's thesis.
Answer the user's question clearly and precisely, citing specific sections or issues when relevant.
Focus on academic quality, methodology, structure, and references.
Respond in the same language the user writes in."""


async def _get_thesis_context(thesis_id: str) -> str:
    """Load thesis text to inject as context into the LLM prompt."""
    import aiofiles
    for ext in ("pdf", "docx"):
        try:
            path = _storage.get_path(thesis_id, ext)
            async with aiofiles.open(path, "rb") as f:
                data = await f.read()
            if ext == "pdf":
                doc = await _pdf_loader.load_from_bytes(data)
            else:
                doc = await _docx_loader.load_from_bytes(data)
            # Limit context to ~6000 words to reduce token usage on free tier
            text = doc["full_text"]
            words = text.split()
            return " ".join(words[:6000])
        except StorageError:
            continue
    raise StorageError(f"Thesis '{thesis_id}' not found.")


@router.post(
    "/question",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a question about an uploaded thesis (auto fallback to free providers)",
)
async def ask_question(body: ChatRequest) -> ChatResponse:
    thesis_context = await _get_thesis_context(body.thesis_id)

    history_text = ""
    for msg in body.history[-6:]:  # last 3 turns
        history_text += f"\n[{msg.role.upper()}]: {msg.content}"

    full_prompt = (
        f"THESIS TEXT (truncated):\n---\n{thesis_context}\n---\n"
        f"{history_text}\n"
        f"[USER]: {body.question}"
    )

    # Use FallbackEngine — it handles quota, retries, and provider switching
    engine = get_fallback_engine()
    request = LLMGenerateRequest(
        provider=body.provider,
        model=body.model,
        prompt=full_prompt,
        system_prompt=body.system_prompt or THESIS_SYSTEM_PROMPT,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
        use_fallback=body.use_fallback,
    )
    result = await engine.generate(request)

    logger.info(
        "Chat question answered",
        extra={
            "thesis_id": body.thesis_id,
            "provider": result.provider,
            "model": result.model,
            "used_fallback": result.used_fallback,
            "cache_hit": result.cache_hit,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
        },
    )

    return ChatResponse(
        thesis_id=body.thesis_id,
        answer=result.text,
        provider=result.provider,
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        finish_reason=result.finish_reason,
        used_fallback=result.used_fallback,
    )
