"""
Authentication and authorization system for AZROI
"""
import jwt
import bcrypt
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from enum import Enum
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
import redis
import asyncio
from functools import wraps

try:
    from ..config.settings import get_security_config, get_redis_config
except ImportError:
    try:
        from config.settings import get_security_config, get_redis_config
    except ImportError:
        from dataclasses import dataclass
        
        @dataclass
        class MockSecurityConfig:
            secret_key: str = "mock_secret_key"
            jwt_algorithm: str = "HS256"
            jwt_expiration: int = 3600
            
        @dataclass
        class MockRedisConfig:
            url: str = "redis://localhost:6379"
            max_connections: int = 10
            
        def get_security_config():
            return MockSecurityConfig()
            
        def get_redis_config():
            return MockRedisConfig()

try:
    from ..app_logging.structured_logging import get_component_logger
except ImportError:
    try:
        from app_logging.structured_logging import get_component_logger
    except ImportError:
        import logging
        def get_component_logger(name):
            return logging.getLogger(name)


class UserRole(Enum):
    ADMIN = "admin"
    USER = "user"
    AGENT = "agent"
    READONLY = "readonly"


class Permission(Enum):
    # General permissions
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    
    # Specific permissions
    AGENT_CREATE = "agent:create"
    AGENT_DELETE = "agent:delete"
    AGENT_EXECUTE = "agent:execute"
    CREW_CREATE = "crew:create"
    CREW_DELETE = "crew:delete"
    CREW_MANAGE = "crew:manage"
    TASK_CREATE = "task:create"
    TASK_CANCEL = "task:cancel"
    SYSTEM_CONFIG = "system:config"
    SYSTEM_MONITOR = "system:monitor"


@dataclass
class User:
    """User model"""
    id: str
    username: str
    email: str
    role: UserRole
    permissions: List[Permission] = field(default_factory=list)
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
    """User session model"""
    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_active: bool = True


class PasswordValidator:
    """Password validation utility"""
    
    @staticmethod
    def validate_password(password: str) -> Dict[str, bool]:
        """Validate password strength"""
        checks = {
            "min_length": len(password) >= 8,
            "has_upper": any(c.isupper() for c in password),
            "has_lower": any(c.islower() for c in password),
            "has_digit": any(c.isdigit() for c in password),
            "has_special": any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password),
        }
        checks["is_valid"] = all(checks.values())
        return checks
    
    @staticmethod
    def generate_secure_password(length: int = 16) -> str:
        """Generate a secure password"""
        import string
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(characters) for _ in range(length))


class PasswordHasher:
    """Password hashing utility"""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def hash_password(self, password: str) -> str:
        """Hash a password"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)


class TokenManager:
    """JWT token management"""
    
    def __init__(self):
        self.config = get_security_config()
        self.logger = get_component_logger("auth")
    
    def create_access_token(self, user: User, expires_delta: Optional[timedelta] = None) -> str:
        """Create an access token"""
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(seconds=self.config.jwt_expiration)
        
        payload = {
            "sub": user.id,
            "username": user.username,
            "role": user.role.value,
            "permissions": [p.value for p in user.permissions],
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access"
        }
        
        token = jwt.encode(payload, self.config.secret_key, algorithm=self.config.jwt_algorithm)
        
        self.logger.info(
            "Access token created",
            user_id=user.id,
            username=user.username,
            expires_at=expire.isoformat()
        )
        
        return token
    
    def create_refresh_token(self, user: User) -> str:
        """Create a refresh token"""
        expire = datetime.now(timezone.utc) + timedelta(days=30)
        
        payload = {
            "sub": user.id,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh"
        }
        
        return jwt.encode(payload, self.config.secret_key, algorithm=self.config.jwt_algorithm)
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode a token"""
        try:
            payload = jwt.decode(
                token,
                self.config.secret_key,
                algorithms=[self.config.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def refresh_access_token(self, refresh_token: str, user: User) -> str:
        """Refresh an access token using a refresh token"""
        payload = self.verify_token(refresh_token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        if payload.get("sub") != user.id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token user mismatch"
            )
        
        return self.create_access_token(user)


class SessionManager:
    """Session management with Redis backend"""
    
    def __init__(self):
        self.redis_config = get_redis_config()
        self.redis_client = None
        self.logger = get_component_logger("session")
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Initialize Redis connection"""
        try:
            import redis
            self.redis_client = redis.from_url(
                self.redis_config.url,
                decode_responses=True,
                max_connections=self.redis_config.max_connections
            )
            # Test connection
            self.redis_client.ping()
            self.logger.info("Redis connection established")
        except Exception as e:
            self.logger.error("Failed to connect to Redis", error=e)
            self.redis_client = None
    
    async def create_session(self, user_id: str, ip_address: str = None, 
                           user_agent: str = None) -> Session:
        """Create a new session"""
        session_id = secrets.token_urlsafe(32)
        created_at = datetime.now(timezone.utc)
        expires_at = created_at + timedelta(hours=24)
        
        session = Session(
            session_id=session_id,
            user_id=user_id,
            created_at=created_at,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if self.redis_client:
            session_data = {
                "user_id": user_id,
                "created_at": created_at.isoformat(),
                "expires_at": expires_at.isoformat(),
                "ip_address": ip_address or "",
                "user_agent": user_agent or "",
                "is_active": "true"
            }
            
            # Store session with expiration
            ttl = int((expires_at - created_at).total_seconds())
            self.redis_client.hset(f"session:{session_id}", mapping=session_data)
            self.redis_client.expire(f"session:{session_id}", ttl)
        
        self.logger.info(
            "Session created",
            session_id=session_id,
            user_id=user_id,
            expires_at=expires_at.isoformat()
        )
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        if not self.redis_client:
            return None
        
        try:
            session_data = self.redis_client.hgetall(f"session:{session_id}")
            if not session_data:
                return None
            
            session = Session(
                session_id=session_id,
                user_id=session_data["user_id"],
                created_at=datetime.fromisoformat(session_data["created_at"]),
                expires_at=datetime.fromisoformat(session_data["expires_at"]),
                ip_address=session_data.get("ip_address") or None,
                user_agent=session_data.get("user_agent") or None,
                is_active=session_data.get("is_active", "true") == "true"
            )
            
            # Check if session is expired
            if session.expires_at < datetime.now(timezone.utc):
                await self.delete_session(session_id)
                return None
            
            return session
        except Exception as e:
            self.logger.error("Failed to get session", session_id=session_id, error=e)
            return None
    
    async def delete_session(self, session_id: str):
        """Delete a session"""
        if self.redis_client:
            self.redis_client.delete(f"session:{session_id}")
        
        self.logger.info("Session deleted", session_id=session_id)
    
    async def delete_user_sessions(self, user_id: str):
        """Delete all sessions for a user"""
        if not self.redis_client:
            return
        
        # Find all sessions for the user
        pattern = "session:*"
        for key in self.redis_client.scan_iter(match=pattern):
            session_data = self.redis_client.hgetall(key)
            if session_data.get("user_id") == user_id:
                self.redis_client.delete(key)
        
        self.logger.info("All user sessions deleted", user_id=user_id)


class RateLimiter:
    """Rate limiting utility"""
    
    def __init__(self):
        self.redis_config = get_redis_config()
        self.security_config = get_security_config()
        self.redis_client = None
        self.logger = get_component_logger("rate_limiter")
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Initialize Redis connection"""
        try:
            import redis
            self.redis_client = redis.from_url(
                self.redis_config.url,
                decode_responses=True
            )
            self.redis_client.ping()
        except Exception as e:
            self.logger.error("Failed to connect to Redis for rate limiting", error=e)
            self.redis_client = None
    
    async def is_rate_limited(self, identifier: str, limit: int = None, 
                            window: int = None) -> bool:
        """Check if an identifier is rate limited"""
        if not self.redis_client or not self.security_config.rate_limit_enabled:
            return False
        
        limit = limit or self.security_config.rate_limit_requests
        window = window or self.security_config.rate_limit_window
        
        key = f"rate_limit:{identifier}"
        
        try:
            pipe = self.redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, window)
            results = pipe.execute()
            
            current_count = results[0]
            
            if current_count > limit:
                self.logger.warning(
                    "Rate limit exceeded",
                    identifier=identifier,
                    current_count=current_count,
                    limit=limit
                )
                return True
            
            return False
        except Exception as e:
            self.logger.error("Rate limiting check failed", identifier=identifier, error=e)
            return False


class AuthenticationService:
    """Main authentication service"""
    
    def __init__(self):
        self.password_hasher = PasswordHasher()
        self.token_manager = TokenManager()
        self.session_manager = SessionManager()
        self.rate_limiter = RateLimiter()
        self.logger = get_component_logger("auth_service")
        
        # In-memory user store (replace with database in production)
        self._users: Dict[str, User] = {}
        self._create_default_admin()
    
    def _create_default_admin(self):
        """Create default admin user"""
        admin_id = "admin"
        if admin_id not in self._users:
            admin_user = User(
                id=admin_id,
                username="admin",
                email="admin@azroi.com",
                role=UserRole.ADMIN,
                permissions=list(Permission)
            )
            self._users[admin_id] = admin_user
            
            # Store hashed password (default: "admin123!")
            self._user_passwords = {
                admin_id: self.password_hasher.hash_password("admin123!")
            }
    
    async def authenticate_user(self, username: str, password: str, 
                              ip_address: str = None) -> Optional[User]:
        """Authenticate a user"""
        # Check rate limiting
        if await self.rate_limiter.is_rate_limited(f"auth:{ip_address or username}"):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many authentication attempts"
            )
        
        # Find user
        user = None
        for u in self._users.values():
            if u.username == username:
                user = u
                break
        
        if not user or not user.is_active:
            self.logger.warning("Authentication failed - user not found", username=username)
            return None
        
        # Verify password
        stored_password = getattr(self, '_user_passwords', {}).get(user.id)
        if not stored_password or not self.password_hasher.verify_password(password, stored_password):
            self.logger.warning("Authentication failed - invalid password", username=username)
            return None
        
        # Update last login
        user.last_login = datetime.now(timezone.utc)
        
        self.logger.info("User authenticated successfully", user_id=user.id, username=username)
        return user
    
    async def create_user(self, username: str, email: str, password: str, 
                         role: UserRole = UserRole.USER) -> User:
        """Create a new user"""
        # Validate password
        validation = PasswordValidator.validate_password(password)
        if not validation["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Password validation failed: {validation}"
            )
        
        # Check if user exists
        for user in self._users.values():
            if user.username == username or user.email == email:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User already exists"
                )
        
        user_id = secrets.token_urlsafe(16)
        user = User(
            id=user_id,
            username=username,
            email=email,
            role=role,
            permissions=self._get_default_permissions(role)
        )
        
        self._users[user_id] = user
        
        # Store hashed password
        if not hasattr(self, '_user_passwords'):
            self._user_passwords = {}
        self._user_passwords[user_id] = self.password_hasher.hash_password(password)
        
        self.logger.info("User created", user_id=user_id, username=username, role=role.value)
        return user
    
    def _get_default_permissions(self, role: UserRole) -> List[Permission]:
        """Get default permissions for a role"""
        permission_map = {
            UserRole.ADMIN: list(Permission),
            UserRole.USER: [
                Permission.READ, Permission.WRITE,
                Permission.AGENT_CREATE, Permission.AGENT_EXECUTE,
                Permission.CREW_CREATE, Permission.TASK_CREATE
            ],
            UserRole.AGENT: [Permission.READ, Permission.AGENT_EXECUTE],
            UserRole.READONLY: [Permission.READ]
        }
        return permission_map.get(role, [Permission.READ])
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self._users.get(user_id)
    
    async def login(self, username: str, password: str, ip_address: str = None, 
                   user_agent: str = None) -> Dict[str, Any]:
        """Login user and create session"""
        user = await self.authenticate_user(username, password, ip_address)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Create session
        session = await self.session_manager.create_session(
            user.id, ip_address, user_agent
        )
        
        # Create tokens
        access_token = self.token_manager.create_access_token(user)
        refresh_token = self.token_manager.create_refresh_token(user)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "session_id": session.session_id,
            "token_type": "bearer",
            "expires_in": get_security_config().jwt_expiration,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role.value,
                "permissions": [p.value for p in user.permissions]
            }
        }
    
    async def logout(self, session_id: str):
        """Logout user and delete session"""
        await self.session_manager.delete_session(session_id)
        self.logger.info("User logged out", session_id=session_id)


# FastAPI dependencies
security = HTTPBearer()
auth_service = AuthenticationService()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """FastAPI dependency to get current authenticated user"""
    try:
        payload = auth_service.token_manager.verify_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user = await auth_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


def require_permission(permission: Permission):
    """Decorator to require specific permission"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs or dependencies
            user = kwargs.get('current_user')
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if permission not in user.permissions and Permission.ADMIN not in user.permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission {permission.value} required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(role: UserRole):
    """Decorator to require specific role"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get('current_user')
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if user.role != role and user.role != UserRole.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role {role.value} required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
