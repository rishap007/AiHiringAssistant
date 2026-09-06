import json

import httpx
import pytest

from app.services.hunar_client import HunarClient, HunarAPIError


AGENT_RESPONSE = {
    "id": "agent_01HUNAR123",
    "name": "Screening Agent",
    "status": "active",
    "custom_variables": {},
    "result_schema": {"type": "object", "properties": {"screened": {"type": "boolean"}}},
}
CALL_RESPONSE = {"id": "call_01HUNAR123", "status": "queued", "request_id": "req-123"}


@pytest.mark.asyncio
async def test_create_agent_posts_hunar_payload() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=AGENT_RESPONSE)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        base_url="https://api.voice.hunar.ai/external/v1", transport=transport, headers={"X-API-Key": "test-key"}
    ) as http_client:
        client = HunarClient(client=http_client)
        result = await client.create_agent(
            "Screening Agent", "ENGLISH", "professional", "Screen candidates", "Screen", "Hello", "Return JSON", AGENT_RESPONSE["result_schema"], "Alex"
        )

    assert result == AGENT_RESPONSE
    assert requests[0].headers["X-API-Key"] == "test-key"
    assert requests[0].url.path == "/external/v1/agents/"
    assert json.loads(requests[0].content)["persona_name"] == "Alex"


@pytest.mark.asyncio
async def test_create_call_posts_hunar_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/external/v1/calls/"
        assert json.loads(request.content) == {
            "agent_id": "agent_01HUNAR123",
            "callee_name": "Asha Rao",
            "mobile_number": "+919876543210",
            "request_id": "req-123",
            "timezone": "Asia/Kolkata",
        }
        return httpx.Response(200, json=CALL_RESPONSE)

    async with httpx.AsyncClient(
        base_url="https://api.voice.hunar.ai/external/v1", transport=httpx.MockTransport(handler)
    ) as http_client:
        result = await HunarClient(client=http_client).create_call(
            "agent_01HUNAR123", "Asha Rao", "+919876543210", request_id="req-123"
        )

    assert result == CALL_RESPONSE


@pytest.mark.asyncio
async def test_non_200_response_raises_hunar_api_error() -> None:
    async with httpx.AsyncClient(
        base_url="https://api.voice.hunar.ai/external/v1",
        transport=httpx.MockTransport(lambda request: httpx.Response(422, json={"success": False, "message": "Invalid call", "details": {"field": "mobile_number"}})),
    ) as http_client:
        with pytest.raises(HunarAPIError) as error:
            await HunarClient(client=http_client).get_call("call-1")

    assert error.value.status_code == 422
    assert error.value.message == "Invalid call"
    assert error.value.details == {"field": "mobile_number"}


@pytest.mark.asyncio
async def test_get_call_uses_trailing_slash() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/external/v1/calls/call-123/"
        return httpx.Response(200, json={"id": "call-123", "status": "COMPLETED"})

    async with httpx.AsyncClient(
        base_url="https://api.voice.hunar.ai/external/v1", transport=httpx.MockTransport(handler)
    ) as http_client:
        result = await HunarClient(client=http_client).get_call("call-123")

    assert result["status"] == "COMPLETED"
