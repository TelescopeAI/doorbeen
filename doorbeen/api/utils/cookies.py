from datetime import datetime, timezone
from typing import Optional

from fastapi import Response

from doorbeen.core.config.execution_env import ExecutionEnv
from doorbeen.core.types.ts_model import TSModel


class ResponseCookies(TSModel):
    response: Response

    class Config:
        arbitrary_types_allowed = True

    def set(self, key: str, value: str, http_only: bool, expires_on: datetime):
        domain: str = 'localhost' if ExecutionEnv.is_local() else 'jointelescope.com'
        same_site = "lax"
        secure = False

        if ExecutionEnv.https_enabled():
            same_site = "none"
            secure = True

        self.response.set_cookie(key=key, value=value, httponly=http_only, secure=secure, samesite=same_site,
                                 domain=domain, expires=expires_on)
        return True

    def delete(self, key: str, http_only: Optional[bool] = False, secure: Optional[bool] = False,
               same_site: Optional[str] = "lax"):
        domain: str = 'localhost' if ExecutionEnv.is_local() else 'jointelescope.com'
        if ExecutionEnv.https_enabled():
            same_site = "none"
            secure = True
        # self.response.delete_cookie(key=key, secure=secure, httponly=http_only, samesite=same_site)
        self.response.set_cookie(key=key, value="", httponly=http_only, secure=secure, samesite=same_site,
                                 domain=domain, expires=datetime(1970, 1, 1, tzinfo=timezone.utc))
        return True
