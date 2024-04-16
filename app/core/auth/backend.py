import uuid

import redis
from fastapi import APIRouter
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    CookieTransport,
)
from fastapi_users.authentication.strategy import RedisStrategy
from httpx_oauth.clients.google import GoogleOAuth2

from app.core.auth.dependancy import get_user_manager
from app.core.settings import get_app_settings
from app.core.settings.base import AppSettings
from app.db.tables import User
from app.user.api.schemas import UserRead, UserUpdate


class AuthBackend:
    def __init__(self, settings: AppSettings) -> None:
        self.cookie_name = settings.cookie_name
        self.cookie_max_age = settings.auth_session_expire_seconds
        self.cookie_transport = CookieTransport(
            cookie_name=self.cookie_name, cookie_max_age=self.cookie_max_age
        )
        self.bearer_transport = BearerTransport(tokenUrl="/user/auth/login")
        self.auth_session_age = settings.auth_session_expire_seconds
        self.google_client_id = settings.google_client_id
        self.google_client_secret = settings.google_client_secret
        self.auth_redis_url = settings.auth_redis_url
        self.auth_backend = AuthenticationBackend(
            name="redis",
            transport=self.bearer_transport,
            get_strategy=self.get_redis_strategy,
        )
        self.components = FastAPIUsers[User, uuid.UUID](
            get_user_manager, [self.auth_backend]
        )
        self.google_oauth_client = GoogleOAuth2(
            self.google_client_id, self.google_client_secret
        )

    @property
    def authenticate_router(self) -> APIRouter:
        return self.components.get_auth_router(self.auth_backend)

    @property
    def oauth_router(self) -> APIRouter:
        return self.components.get_oauth_router(
            auth_backend.google_oauth_client,
            auth_backend.auth_backend,
            state_secret="SECRET",  # TODO: 정확한 사용법을 확인 후 수정
            associate_by_email=True,
        )

    @property
    def password_reset_router(self) -> APIRouter:
        return self.components.get_reset_password_router()

    @property
    def users_router(self) -> APIRouter:
        return self.components.get_users_router(
            user_schema=UserRead, user_update_schema=UserUpdate
        )

    def get_redis_strategy(self) -> RedisStrategy:
        redis_client = redis.asyncio.from_url(
            self.auth_redis_url, decode_responses=True
        )
        return RedisStrategy(
            redis=redis_client,
            lifetime_seconds=self.auth_session_age,
            key_prefix="auth-session-id:",
        )


auth_backend = AuthBackend(settings=get_app_settings())
