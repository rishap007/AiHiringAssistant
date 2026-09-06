from faker import Faker

from app.services.people_search.base import CandidateResult, PeopleSearchClient


class MockPeopleSearchClient(PeopleSearchClient):
    async def search(self, criteria: dict, limit: int = 10) -> list[CandidateResult]:
        faker = Faker()
        faker.seed_instance(20240905)
        title = criteria.get("title", "the role")
        location = criteria.get("location", "an unspecified location")
        return [
            CandidateResult(
                name=faker.name(),
                phone_e164=None,
                email=faker.email(),
                headline=f"{title} professional based in {location}",
                source="mock",
                source_ref=f"mock-{index + 1}",
            )
            for index in range(limit)
        ]
