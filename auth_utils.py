from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import secrets
import string

from config import settings
import models
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Deque, Dict

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# Use bcrypt_sha256 to avoid the 72-byte bcrypt password limit while
# remaining compatible with existing bcrypt hashes.
pwd_context = CryptContext(
    schemes=["bcrypt_sha256", "bcrypt"],
    deprecated="auto"
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# Simple in-memory login attempt tracking (per-process best-effort)
_login_attempts: Dict[str, Deque[datetime]] = defaultdict(deque)
_LOCKOUT_WINDOW_SECONDS = 300  # 5 minutes
_MAX_ATTEMPTS = 10

def _prune_attempts(identifier: str) -> None:
    window_start = datetime.utcnow() - timedelta(seconds=_LOCKOUT_WINDOW_SECONDS)
    attempts = _login_attempts[identifier]
    while attempts and attempts[0] < window_start:
        attempts.popleft()

def is_login_allowed(identifier: str) -> bool:
    _prune_attempts(identifier)
    return len(_login_attempts[identifier]) < _MAX_ATTEMPTS

def register_login_failure(identifier: str) -> None:
    _prune_attempts(identifier)
    _login_attempts[identifier].append(datetime.utcnow())

def register_login_success(identifier: str) -> None:
    _login_attempts.pop(identifier, None)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    # Force bcrypt_sha256 to avoid bcrypt's 72-byte limit and backend quirks
    return pwd_context.hash(password, scheme="bcrypt_sha256")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await models.User.find_one(models.User.email == email)
    if user is None:
        raise credentials_exception
    return user

async def get_admin_user(current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

def generate_unique_affiliate_link():
    """Generate a unique link for affiliates"""
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(20))
