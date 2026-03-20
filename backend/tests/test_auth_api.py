"""Tests for authentication API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.narrative import User
from app.services.auth_service import hash_password


class TestAuthRegister:
    """Tests for POST /api/auth/register endpoint."""

    @pytest.mark.asyncio
    async def test_register_success(self, db_session: AsyncSession):
        """Should register a new user successfully."""
        from main import app
        from app.core.database import get_db
        
        app.dependency_overrides[get_db] = lambda: db_session
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/auth/register",
                json={
                    "email": "test@example.com",
                    "password": "testpassword123",
                    "full_name": "Test User"
                }
            )
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, db_session: AsyncSession):
        """Should fail when registering with existing email."""
        from main import app
        from app.core.database import get_db
        
        user = User(
            email="existing@example.com",
            hashed_password=hash_password("password123"),
            full_name="Existing User"
        )
        db_session.add(user)
        await db_session.commit()
        
        app.dependency_overrides[get_db] = lambda: db_session
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/auth/register",
                json={
                    "email": "existing@example.com",
                    "password": "newpassword123",
                    "full_name": "New User"
                }
            )
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]


class TestAuthLogin:
    """Tests for POST /api/auth/login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(self, db_session: AsyncSession):
        """Should login successfully with correct credentials."""
        from main import app
        from app.core.database import get_db
        
        user = User(
            email="login@example.com",
            hashed_password=hash_password("correctpassword"),
            full_name="Login User",
            is_active=True
        )
        db_session.add(user)
        await db_session.commit()
        
        app.dependency_overrides[get_db] = lambda: db_session
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/auth/login",
                data={
                    "username": "login@example.com",
                    "password": "correctpassword"
                }
            )
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, db_session: AsyncSession):
        """Should fail with wrong password."""
        from main import app
        from app.core.database import get_db
        
        user = User(
            email="wrongpass@example.com",
            hashed_password=hash_password("correctpassword"),
            is_active=True
        )
        db_session.add(user)
        await db_session.commit()
        
        app.dependency_overrides[get_db] = lambda: db_session
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/auth/login",
                data={
                    "username": "wrongpass@example.com",
                    "password": "wrongpassword"
                }
            )
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, db_session: AsyncSession):
        """Should fail with nonexistent user."""
        from main import app
        from app.core.database import get_db
        
        app.dependency_overrides[get_db] = lambda: db_session
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/auth/login",
                data={
                    "username": "nonexistent@example.com",
                    "password": "anypassword"
                }
            )
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 401


class TestAuthMe:
    """Tests for GET /api/auth/me endpoint."""

    @pytest.mark.asyncio
    async def test_me_with_valid_token(self, db_session: AsyncSession):
        """Should return user info with valid token."""
        from main import app
        from app.core.database import get_db
        from app.services.auth_service import create_access_token
        import uuid
        
        user_id = str(uuid.uuid4())
        user = User(
            id=uuid.UUID(user_id),
            email="me@example.com",
            hashed_password=hash_password("password"),
            full_name="Me User",
            is_active=True
        )
        db_session.add(user)
        await db_session.commit()
        
        token = create_access_token(data={"sub": user_id})
        
        app.dependency_overrides[get_db] = lambda: db_session
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "me@example.com"

    @pytest.mark.asyncio
    async def test_me_without_token(self, db_session: AsyncSession):
        """Should fail without token."""
        from main import app
        from app.core.database import get_db
        
        app.dependency_overrides[get_db] = lambda: db_session
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/auth/me")
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 401


class TestAuthLogout:
    """Tests for POST /api/auth/logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_success(self, db_session: AsyncSession):
        """Should return success message on logout."""
        from main import app
        from app.core.database import get_db
        
        app.dependency_overrides[get_db] = lambda: db_session
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post("/api/auth/logout")
        
        app.dependency_overrides.clear()
        
        assert response.status_code == 200
        assert "logged out" in response.json()["message"].lower()
