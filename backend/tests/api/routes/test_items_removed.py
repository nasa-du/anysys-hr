from fastapi.testclient import TestClient

from app.core.config import settings

ITEMS_PATH = f"{settings.API_V1_STR}/items"


def test_items_endpoint_is_gone(client: TestClient) -> None:
    response = client.get(f"{ITEMS_PATH}/")

    assert response.status_code == 404


def test_items_are_not_in_the_openapi_schema(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    operation_tags = {
        tag
        for path_item in schema["paths"].values()
        for operation in path_item.values()
        if isinstance(operation, dict)
        for tag in operation.get("tags", [])
    }
    assert "items" not in operation_tags
    assert not [
        path
        for path in schema["paths"]
        if path == ITEMS_PATH or path.startswith(f"{ITEMS_PATH}/")
    ]
