import os
import logging
from fastapi import Header, HTTPException, Depends
from jose import jwt, JWTError

logger = logging.getLogger("auth")

def get_current_user_id(authorization: str = Header(None)) -> str:
    if not authorization:
        if os.getenv("DEBUG", "false").lower() == "true":
            return "mock_user_id"
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != 'bearer':
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
        
        # Decode the token
        payload = jwt.get_unverified_claims(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing sub claim")
        
        # Log crucial pour débugger la liaison entre auth et DB
        logger.info(f"AUTH: Accès par user_id={user_id}")
        
        return user_id
    except (ValueError, JWTError):
        raise HTTPException(status_code=401, detail="Invalid token format")
