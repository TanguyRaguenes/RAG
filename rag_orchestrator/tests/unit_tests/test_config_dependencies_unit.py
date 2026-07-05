import json
from types import SimpleNamespace

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api import dependencies
from app.core import config as config_module
from app.schemas.authenticated_user_schema import AuthenticatedUser


def test_get_config_and_db_pool_return_app_state_values() -> None:
    config = {"llm": {}}
    db_pool = object()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(config=config, db_pool=db_pool)))

    assert dependencies.get_config(request) is config
    assert dependencies.get_db_pool(request) is db_pool


def test_load_config_reads_json_file(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"llm": {"model": "test"}}), encoding="utf-8")
    monkeypatch.setattr(config_module, "_CONFIG_PATH", config_path)

    assert config_module.load_config() == {"llm": {"model": "test"}}


@pytest.mark.asyncio
async def test_get_current_user_requires_credentials() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await dependencies.get_current_user(credentials=None, auth_service=object())

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_maps_jwt_errors_to_401() -> None:
    class FailingAuthService:
        async def authenticate(self, token: str):
            raise jwt.PyJWTError("invalid")

    with pytest.raises(HTTPException) as exc_info:
        await dependencies.get_current_user(
            credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad"),
            auth_service=FailingAuthService(),
        )

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_returns_authenticated_user() -> None:
    expected = AuthenticatedUser(sub="user")

    class AuthService:
        async def authenticate(self, token: str):
            assert token == "token"
            return expected

    result = await dependencies.get_current_user(
        credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials="token"),
        auth_service=AuthService(),
    )

    assert result is expected
