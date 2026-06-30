"""Tavily-backed public job search boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlparse, urlunparse

from app.core.config import settings


_TAVILY_DEFAULT_KEY = "your-tavily-api-key"


class SearchServiceError(RuntimeError):
    """Safe provider error that route handlers can convert to HTTP 502."""


class TavilyClientProtocol(Protocol):
    async def search(
        self,
        query: str,
        *,
        max_results: int,
        search_depth: str | None = None,
        include_raw_content: bool | str | None = None,
        include_images: bool | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Return Tavily-compatible search payload."""


@dataclass(frozen=True)
class SearchResult:
    """Normalized public search result returned to ingestion routes."""

    url: str
    title: str | None = None
    content: str | None = None
    score: float | None = None
    published_date: str | None = None


class TavilySearchService:
    """Small injectable wrapper around Tavily search calls."""

    def __init__(
        self,
        *,
        client: TavilyClientProtocol | None = None,
    ) -> None:
        self._client = client

    async def search_jobs(
        self,
        query: str,
        max_urls: int | None = None,
    ) -> list[SearchResult]:
        """Search public web results and return normalized URL metadata."""

        requested_limit = max_urls if max_urls is not None else settings.MAX_URLS_PER_BATCH
        result_limit = self._clamp_max_urls(requested_limit)

        try:
            response = await self._get_client().search(
                query,
                max_results=result_limit,
                search_depth="basic",
                include_raw_content=False,
                include_images=False,
                timeout=float(settings.REQUEST_TIMEOUT_SECONDS),
            )
        except SearchServiceError:
            raise
        except Exception as exc:
            raise SearchServiceError("Tavily search failed") from exc

        raw_results = response.get("results", [])
        if not isinstance(raw_results, list):
            raise SearchServiceError("Tavily search returned an invalid response")

        normalized_results: list[SearchResult] = []
        for raw_result in raw_results[:result_limit]:
            normalized = self._normalize_result(raw_result)
            if normalized is not None:
                normalized_results.append(normalized)
        return normalized_results

    def _get_client(self) -> TavilyClientProtocol:
        if self._client is not None:
            return self._client

        api_key = settings.TAVILY_API_KEY.get_secret_value()
        if not api_key or api_key == _TAVILY_DEFAULT_KEY:
            raise SearchServiceError("Tavily API key is not configured")

        try:
            from tavily import AsyncTavilyClient
        except ImportError as exc:
            raise SearchServiceError("Tavily client dependency is not installed") from exc

        self._client = AsyncTavilyClient(api_key=api_key)
        return self._client

    def _clamp_max_urls(self, requested_max_urls: int) -> int:
        configured_limit = max(1, settings.MAX_URLS_PER_BATCH)
        return max(1, min(requested_max_urls, configured_limit))

    def _normalize_result(self, raw_result: Any) -> SearchResult | None:
        if not isinstance(raw_result, dict):
            return None

        url = _normalize_public_url(raw_result.get("url"))
        if url is None:
            return None

        return SearchResult(
            url=url,
            title=_optional_str(raw_result.get("title")),
            content=_optional_str(raw_result.get("content")),
            score=_optional_float(raw_result.get("score")),
            published_date=_optional_str(raw_result.get("published_date")),
        )


def _normalize_public_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None

    return urlunparse(parsed._replace(fragment=""))


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


search_service = TavilySearchService()
