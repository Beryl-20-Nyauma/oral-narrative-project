"""Authentication service with JWT tokens and password hashing."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from jose import JWTError, jwt

from config import get_settings
from app.models.narrative import User

logger = logging.getLogger(__name__)
settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password for storing."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a stored password against one provided by user."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional custom expiration time
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded payload or None if invalid
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode failed: {e}")
        return None


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """
    Get user by email address.
    
    Args:
        db: Database session
        email: User email
    
    Returns:
        User instance or None
    """
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    """
    Get user by ID.
    
    Args:
        db: Database session
        user_id: User UUID
    
    Returns:
        User instance or None
    """
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """
    Authenticate a user by email and password.
    
    Args:
        db: Database session
        email: User email
        password: Plain text password
    
    Returns:
        User instance if authenticated, None otherwise
    """
    user = await get_user_by_email(db, email)
    
    if not user:
        return None
    
    if not user.is_active:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    user.last_login = datetime.utcnow()
    await db.commit()
    
    return user


async def create_user(
    db: AsyncSession,
    email: str,
    password: str,
    full_name: Optional[str] = None,
    is_admin: bool = False
) -> User:
    """
    Create a new user.
    
    Args:
        db: Database session
        email: User email
        password: Plain text password
        full_name: Optional full name
        is_admin: Whether user is admin
    
    Returns:
        New User instance
    """
    hashed_password = hash_password(password)
    
    user = User(
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        is_admin=is_admin,
        is_active=True
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    logger.info(f"Created user: {email}")
    return user


async def update_user(
    db: AsyncSession,
    user_id: str,
    **kwargs
) -> Optional[User]:
    """
    Update user fields.
    
    Args:
        db: Database session
        user_id: User UUID
        **kwargs: Fields to update
    
    Returns:
        Updated User or None
    """
    user = await get_user_by_id(db, user_id)
    
    if not user:
        return None
    
    for key, value in kwargs.items():
        if hasattr(user, key):
            if key == "password":
                value = hash_password(value)
                key = "hashed_password"
            setattr(user, key, value)
    
    await db.commit()
    await db.refresh(user)
    
    return user


async def delete_user(db: AsyncSession, user_id: str) -> bool:
    """
    Delete a user.
    
    Args:
        db: Database session
        user_id: User UUID
    
    Returns:
        True if deleted, False if not found
    """
    user = await get_user_by_id(db, user_id)
    
    if not user:
        return False
    
    await db.delete(user)
    await db.commit()
    
    logger.info(f"Deleted user: {user.email}")
    return True
