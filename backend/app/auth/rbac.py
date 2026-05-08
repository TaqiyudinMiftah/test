from functools import wraps
from fastapi import HTTPException, status
from app.models.user import UserRole

def require_role(*allowed_roles: UserRole):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Autentikasi diperlukan"
                )
            if current_user.role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Anda tidak memiliki izin untuk mengakses resource ini"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator

require_admin = require_role(UserRole.ADMIN)
require_editor = require_role(UserRole.ADMIN, UserRole.EDITOR)
require_viewer = require_role(UserRole.ADMIN, UserRole.EDITOR, UserRole.VIEWER)
