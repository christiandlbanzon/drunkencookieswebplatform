from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.auth.jwt_handler import decode_access_token
from app.auth.roles import Role, ROLE_PERMISSIONS

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.query(User).filter(User.id == int(user_id), User.is_active.is_(True)).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_role(*roles: Role):
    """Dependency that restricts access to specific roles."""
    def _check(current_user: User = Depends(get_current_user)):
        if current_user.role not in [r.value for r in roles]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user
    return _check


def require_module(module: str):
    """Dependency that restricts access based on module permissions."""
    def _check(current_user: User = Depends(get_current_user)):
        user_role = Role(current_user.role)
        allowed_modules = ROLE_PERMISSIONS.get(user_role, set())
        if module not in allowed_modules:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied for this module")
        return current_user
    return _check
