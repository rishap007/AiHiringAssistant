from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.services.people_search.base import CandidateResult, PeopleSearchClient


class ApolloPeopleSearchClient(PeopleSearchClient):
    endpoint = "https://api.apollo.io/v1/mixed_people/api_search"

    async def search(self, criteria: dict, limit: int = 10) -> list[CandidateResult]:
        params: dict[str, Any] = {
            "page": 1,
            "per_page": limit,
            "q_keywords": ", ".join(criteria.get("keywords", []) or criteria.get("skills", [])),
        }
        if criteria.get("title"):
            params["person_titles[]"] = criteria["title"]
        if criteria.get("seniority"):
            params["person_seniorities[]"] = criteria["seniority"]
        if criteria.get("location"):
            params["person_locations[]"] = criteria["location"]

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self.endpoint,
                params=params,
                headers={"X-Api-Key": settings.people_search_api_key or ""},
            )
            response.raise_for_status()
            payload = response.json()

        people = payload.get("people", [])
        results: list[CandidateResult] = []
        for person in people[:limit]:
            phone = person.get("phone_number") or person.get("mobile_phone")
            results.append(
                CandidateResult(
                    name=person.get("name") or "Unknown candidate",
                    phone_e164=phone,
                    email=person.get("email"),
                    headline=person.get("headline") or person.get("title") or "",
                    source="apollo",
                    source_ref=str(person.get("id") or person.get("email") or person.get("name")),
                )
            )
        return results
