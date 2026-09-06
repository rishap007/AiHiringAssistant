from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class CandidateResult:
    name: str
    phone_e164: str | None
    email: str | None
    headline: str
    source: str
    source_ref: str


class PeopleSearchClient(ABC):
    @abstractmethod
    async def search(self, criteria: dict, limit: int = 10) -> list[CandidateResult]:
        raise NotImplementedError
