from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.config import get_settings
from app.auth.schemas import UserCreate, UserLogin, TokenResponse, TokenData
from app.storage import storage as default_storage, User
from app.validation import ValidationError

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    # Ensure sub is string as per JWT spec
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        email: str = payload.get("email")
        if user_id_str is None:
            return None
        return TokenData(user_id=int(user_id_str), email=email)
    except (JWTError, ValueError):
        return None


class AuthService:
    """Authentication service class for dependency injection."""
    
    def __init__(self, storage_instance=None):
        self.storage = storage_instance or default_storage
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return verify_password(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        return get_password_hash(password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        return create_access_token(data, expires_delta)
    
    def decode_access_token(self, token: str) -> Optional[TokenData]:
        return decode_access_token(token)
    
    def signup(self, user_data: UserCreate) -> User:
        """Create a new user."""
        # Check if email exists
        if self.storage.get_user_by_email(user_data.email):
            raise ValidationError("email_already_exists", "Email already exists")
        
        # Check if handle exists
        if self.storage.get_user_by_handle(user_data.handle):
            raise ValidationError("handle_already_exists", "Handle already exists")
        
        # Hash password
        password_hash = self.get_password_hash(user_data.password)
        
        # Create user
        user = self.storage.create_user(
            email=user_data.email,
            password=user_data.password,
            display_name=user_data.display_name,
            handle=user_data.handle
        )
        return user
    
    def login(self, login_data: UserLogin) -> TokenResponse:
        """Authenticate user and return token."""
        user = self.storage.get_user_by_email(login_data.email)
        if not user:
            raise ValidationError("invalid_credentials", "Invalid credentials")
        
        if not self.verify_password(login_data.password, user.password_hash):
            raise ValidationError("invalid_credentials", "Invalid credentials")
        
        # Create token
        token = self.storage.create_token(user.id)
        
        return TokenResponse(
            token=token,
            user_id=user.id,
            display_name=user.display_name
        )
    
    def get_current_user(self, token: str) -> User:
        """Get user from token."""
        user = self.storage.get_user_by_token(token)
        if not user:
            raise ValidationError("invalid_token", "Invalid token")
        return user


auth_service = AuthService()