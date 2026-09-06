from app.core.config import settings
from app.services.people_search.apollo_client import ApolloPeopleSearchClient
from app.services.people_search.base import PeopleSearchClient
from app.services.people_search.mock_client import MockPeopleSearchClient


def get_people_search_client() -> PeopleSearchClient:
    if settings.people_search_provider.lower() == "apollo" and settings.people_search_api_key:
        return ApolloPeopleSearchClient()
    return MockPeopleSearchClient()
