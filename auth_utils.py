from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends
import hashlib
import secrets
import string
from fastapi import HTTPException
from fastapi import status

from config import settings
import models
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Deque, Dict
from email_service import email_service

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# Simple password hashing using SHA256 + salt
def simple_hash_password(password: str) -> str:
    """Simple password hashing using SHA256 with salt"""
    salt = secrets.token_hex(16)  # 32 character salt
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{password_hash}"

def simple_verify_password(password: str, hashed_password: str) -> bool:
    """Simple password verification"""
    try:
        salt, stored_hash = hashed_password.split(":", 1)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return password_hash == stored_hash
    except:
        return False

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
    """Verify password using simple hashing"""
    return simple_verify_password(plain_password, hashed_password)

def get_password_hash(password):
    """Hash password using simple hashing"""
    return simple_hash_password(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_token_from_header(authorization: str = None):
    """Extract token from Authorization header"""
    if not authorization:
        return None
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None
        return token
    except:
        return None

async def get_current_user(token: str = None):
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    try:
        user = await models.User.find_one(models.User.email == email)
        if user is None:
            raise credentials_exception
        return user
    except Exception as e:
        print(f"Database error during user lookup: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable"
        )

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

def generate_verification_token():
    """Generate a secure verification token"""
    return secrets.token_urlsafe(32)

def generate_verification_code():
    """Generate a 6-digit verification code"""
    return ''.join(secrets.choice('0123456789') for _ in range(6))

async def create_verification_token(email: str, token_type: str) -> str:
    """Create and store email verification token"""
    token = generate_verification_token()
    expires_at = datetime.utcnow() + timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS)
    
    # Create verification token record
    verification_token = models.EmailVerificationToken(
        email=email,
        token=token,
        token_type=token_type,
        expires_at=expires_at
    )
    await verification_token.insert()
    
    return token

async def create_verification_code(email: str, token_type: str) -> str:
    """Create and store email verification code (6 digits)"""
    code = generate_verification_code()
    expires_at = datetime.utcnow() + timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS)
    
    # Create verification token record with code
    verification_token = models.EmailVerificationToken(
        email=email,
        token=code,  # Store code as token
        token_type=token_type,
        expires_at=expires_at
    )
    await verification_token.insert()
    
    return code

async def verify_email_token(token: str) -> Optional[models.EmailVerificationToken]:
    """Verify email token and return token record if valid"""
    try:
        # Find token
        token_record = await models.EmailVerificationToken.find_one(
            models.EmailVerificationToken.token == token
        )
        
        if not token_record:
            return None
        
        # Check if already used
        if token_record.is_used:
            return None
        
        # Check if expired
        if datetime.utcnow() > token_record.expires_at:
            return None
        
        return token_record
        
    except Exception as e:
        print(f"Error verifying token: {e}")
        return None

async def mark_token_as_used(token_record: models.EmailVerificationToken):
    """Mark verification token as used"""
    token_record.is_used = True
    token_record.used_at = datetime.utcnow()
    await token_record.save()

async def send_verification_email(email: str, token: str, user_type: str) -> bool:
    """Send verification email using email service"""
    if not settings.EMAIL_VERIFICATION_ENABLED:
        return True  # Skip email verification if disabled
    
    return await email_service.send_verification_email(email, token, user_type)

async def send_welcome_email(email: str, user_type: str, name: str = None) -> bool:
    """Send welcome email after successful verification"""
    if not settings.EMAIL_VERIFICATION_ENABLED:
        return True  # Skip welcome email if disabled
    
    return await email_service.send_welcome_email(email, user_type, name)
