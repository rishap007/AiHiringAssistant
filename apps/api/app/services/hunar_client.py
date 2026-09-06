from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from app.core.config import settings


class HunarAPIError(Exception):
    """Raised when the Hunar API returns a non-success response."""

    def __init__(self, status_code: int, message: str, details: Any = None) -> None:
        self.status_code = status_code
        self.message = message
        self.details = details
        super().__init__(f"Hunar API error ({status_code}): {message}")


class HunarClient:
    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        base_url: str | None = None,
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            # Keep the trailing slash so relative endpoint paths preserve the
            # `/external/v1` path in HUNAR_BASE_URL.
            base_url=(base_url or settings.hunar_base_url).rstrip("/") + "/",
            headers={"X-API-Key": settings.hunar_api_key},
        )
        self._client.headers.setdefault("X-API-Key", settings.hunar_api_key)

    async def __aenter__(self) -> "HunarClient":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = await self._client.request(method, path, **kwargs)
        if response.status_code != 200:
            try:
                payload = response.json()
            except ValueError:
                payload = {}
            if isinstance(payload, Mapping):
                message = str(payload.get("message") or response.text or "Request failed")
                details = payload.get("details")
            else:
                message = response.text or "Request failed"
                details = None
            raise HunarAPIError(response.status_code, message, details)
        if not response.content:
            return {}
        return response.json()

    async def list_agents(self, page: int = 1, page_size: int = 20) -> dict:
        return await self._request("GET", "agents/", params={"page": page, "page_size": page_size})

    async def get_agent(self, agent_id: str) -> dict:
        return await self._request("GET", f"agents/{agent_id}")

    async def create_agent(
        self,
        name: str,
        language: str,
        voice_persona: str,
        agent_prompt: str,
        objective: str,
        introduction: str,
        result_prompt: str,
        result_schema: dict,
        persona_name: str | None = None,
    ) -> dict:
        payload: dict[str, Any] = {
            "name": name,
            "language": language,
            "voice_persona": voice_persona,
            "agent_prompt": agent_prompt,
            "objective": objective,
            "introduction": introduction,
            "result_prompt": result_prompt,
            "result_schema": result_schema,
        }
        if persona_name is not None:
            payload["persona_name"] = persona_name
        return await self._request("POST", "agents/", json=payload)

    async def create_call(
        self,
        agent_id: str,
        callee_name: str,
        mobile_number: str,
        custom_data: dict | None = None,
        request_id: str | None = None,
        callback_config: dict | None = None,
        retry_config: dict | None = None,
        guardrails: dict | None = None,
        timezone: str = "Asia/Kolkata",
    ) -> dict:
        payload: dict[str, Any] = {
            "agent_id": agent_id,
            "callee_name": callee_name,
            "mobile_number": mobile_number,
            "timezone": timezone,
        }
        for key, value in {
            "custom_data": custom_data,
            "request_id": request_id,
            "callback_config": callback_config,
            "retry_config": retry_config,
            "guardrails": guardrails,
        }.items():
            if value is not None:
                payload[key] = value
        return await self._request("POST", "calls/", json=payload)

    async def create_bulk_calls(self, agent_id: str, data: list[dict], **shared_options: Any) -> list[dict]:
        payload = {"agent_id": agent_id, "data": data, **shared_options}
        return await self._request("POST", "calls/bulk/", json=payload)

    async def get_call(self, call_id: str) -> dict:
        return await self._request("GET", f"calls/{call_id}/")

    async def list_calls(
        self,
        status: str | None = None,
        agent_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if status is not None:
            params["status"] = status
        if agent_id is not None:
            params["agent_id"] = agent_id
        return await self._request("GET", "calls/", params=params)

    async def list_numbers(self, page: int = 1, page_size: int = 10) -> dict:
        return await self._request("GET", "numbers/", params={"page": page, "page_size": page_size})
