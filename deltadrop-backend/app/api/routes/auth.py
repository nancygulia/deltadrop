from datetime import datetime, timedelta, timezone
from hashlib import sha256
import requests

<<<<<<< HEAD
from fastapi import APIRouter, Depends, HTTPException, Request, status
=======
from fastapi import APIRouter, Depends, HTTPException, status
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    get_current_user,
)
from app.core.config import settings
from app.core.apple_keys import get_apple_public_key
from app.db.session import get_db
from app.models.user import User
from app.models.user import RefreshToken
from app.utils.email import send_password_reset_email
<<<<<<< HEAD
from app.core.rate_limit import rate_limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])

import logging as _logging
_auth_logger = _logging.getLogger("deltadrop.auth")

=======

router = APIRouter(prefix="/auth", tags=["Authentication"])

>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3

# ── Schemas ────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email:     EmailStr
    username:  str
    password:  str
    full_name: str | None = None

class LoginRequest(BaseModel):
    email:    EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    user:          dict

class RefreshRequest(BaseModel):
    refresh_token: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token:        str
    new_password: str

class ProfileUpdateRequest(BaseModel):
    full_name: str | None = None
    email:     EmailStr | None = None


class GoogleLoginRequest(BaseModel):
    token: str | None = None
    credential: str | None = None

class AppleLoginRequest(BaseModel):
    identity_token: str
    email: str | None = None
    full_name: str | None = None


def _verify_google_token(token: str, token_type: str) -> dict:
    """Verify a Google token and return the decoded user info."""
    if not settings.GOOGLE_CLIENT_ID:
        raise RuntimeError("GOOGLE_CLIENT_ID is not configured")

    if token_type == 'id_token':
        response = requests.get(
            'https://oauth2.googleapis.com/tokeninfo',
            params={'id_token': token},
            timeout=10,
        )
        if response.status_code != 200:
            raise ValueError('Invalid Google ID token')

        id_info = response.json()
        if id_info.get('aud') != settings.GOOGLE_CLIENT_ID:
            raise ValueError('Google token audience mismatch')
        if id_info.get('iss') not in ('accounts.google.com', 'https://accounts.google.com'):
            raise ValueError('Invalid Google token issuer')
        return id_info

    response = requests.get(
        'https://www.googleapis.com/oauth2/v3/userinfo',
        headers={'Authorization': f'Bearer {token}'},
        timeout=10,
    )
    if response.status_code != 200:
        raise ValueError('Invalid Google access token')

    return response.json()


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/register", status_code=201)
<<<<<<< HEAD
async def register(body: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    # Rate limit: 3 registrations per minute per IP
    rate_limiter.check(request, "register", max_requests=3, window_seconds=60)

=======
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
    email_norm = body.email.lower().strip()
    # Check email exists
    result = await db.execute(select(User).where(User.email == email_norm))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Check username exists
    result = await db.execute(select(User).where(User.username == body.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")

    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user = User(
        email         = email_norm,
        username      = body.username,
        password_hash = hash_password(body.password),
        full_name     = body.full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {"success": True, "message": "Account created. Please sign in."}


@router.post("/login", response_model=TokenResponse)
<<<<<<< HEAD
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    # Rate limit: 5 login attempts per minute per IP
    rate_limiter.check(request, "login", max_requests=5, window_seconds=60)

=======
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
    email_norm = body.email.lower().strip()
    result = await db.execute(select(User).where(User.email == email_norm))
    user   = result.scalar_one_or_none()

<<<<<<< HEAD
    client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if not client_ip:
        client_ip = request.client.host if request.client else "unknown"

    if not user:
        _auth_logger.warning(f"Login FAILED: unknown email {email_norm} from IP {client_ip}")
=======
    if not user:
        import logging
        logging.getLogger("uvicorn").warning(f"Auth failed: User not found for {email_norm}")
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
        raise HTTPException(status_code=401, detail="Invalid email or password")

    is_verified = verify_password(body.password, user.password_hash)
    if not is_verified:
<<<<<<< HEAD
        _auth_logger.warning(f"Login FAILED: wrong password for {email_norm} from IP {client_ip}")
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        _auth_logger.warning(f"Login FAILED: disabled account {email_norm} from IP {client_ip}")
=======
        import logging
        logging.getLogger("uvicorn").warning(f"Auth failed: Password verification failed for {email_norm}")
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
        raise HTTPException(status_code=403, detail="Account disabled")

    access_token  = create_access_token({"sub": str(user.id), "role": user.role.value})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    # Store hashed refresh token
    token_hash = sha256(refresh_token.encode()).hexdigest()
    db.add(RefreshToken(
        user_id    = user.id,
        token_hash = token_hash,
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    ))
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id":        user.id,
            "email":     user.email,
            "username":  user.username,
            "full_name": user.full_name,
            "role":      user.role.value,
        }
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload    = decode_token(body.refresh_token)
    token_hash = sha256(body.refresh_token.encode()).hexdigest()

    result     = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked    == False,
        ).with_for_update()
    )
    stored_token = result.scalar_one_or_none()
    if not stored_token:
        raise HTTPException(status_code=401, detail="Refresh token invalid or revoked")

    if stored_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    # Revoke old token
    stored_token.revoked = True
    await db.flush()

    # Fetch user
    result = await db.execute(select(User).where(User.id == int(payload["sub"])))
    user   = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    # Issue new tokens
    new_access  = create_access_token({"sub": str(user.id), "role": user.role.value})
    new_refresh = create_refresh_token({"sub": str(user.id)})

    new_hash = sha256(new_refresh.encode()).hexdigest()
    db.add(RefreshToken(
        user_id    = user.id,
        token_hash = new_hash,
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    ))
    await db.commit()

    return TokenResponse(
        access_token=new_access, refresh_token=new_refresh,
        user={"id": user.id, "email": user.email, "username": user.username, "role": user.role.value}
    )


@router.post("/logout")
async def logout(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token_hash = sha256(body.refresh_token.encode()).hexdigest()
    result     = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    token      = result.scalar_one_or_none()
    if token:
        token.revoked = True
        await db.commit()
    return {"success": True, "message": "Logged out"}


@router.post("/google-login", response_model=TokenResponse)
<<<<<<< HEAD
async def google_login(body: GoogleLoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    # Rate limit: 10 Google login attempts per minute per IP
    rate_limiter.check(request, "google-login", max_requests=10, window_seconds=60)

=======
async def google_login(body: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
    """
    Verifies a Google OAuth access token or ID token, creates or identifies the user, and issues JWT tokens.
    """
    import logging
    import secrets
    import string

    logger = logging.getLogger("uvicorn")

    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is temporarily unavailable",
        )

    try:
        token = body.token or body.credential
        if not token:
            raise ValueError("Google token is missing")

        token_type = 'id_token' if body.credential else 'access_token'
        id_info = _verify_google_token(token, token_type)
        email_norm = id_info['email'].lower().strip()
        full_name = id_info.get('name', '')

        result = await db.execute(select(User).where(User.email == email_norm))
        user   = result.scalar_one_or_none()

        if not user:
            logger.info(f"✨ Creating new Google account for {email_norm}")
            username = f"{email_norm.split('@')[0]}_{secrets.token_hex(2)}"
            random_pw = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
            
            user = User(
                email         = email_norm,
                username      = username,
                password_hash = hash_password(random_pw),
                full_name     = full_name,
                is_active     = True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        else:
            if not user.is_active:
                raise HTTPException(status_code=403, detail="Account disabled")
            logger.info(f"🔑 Google login for existing user: {email_norm}")

        # Issue standard tokens
        access_token  = create_access_token({"sub": str(user.id), "role": user.role.value})
        refresh_token = create_refresh_token({"sub": str(user.id)})

        token_hash = sha256(refresh_token.encode()).hexdigest()
        db.add(RefreshToken(
            user_id    = user.id,
            token_hash = token_hash,
            expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        ))
        await db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user={
                "id":        user.id,
                "email":     user.email,
                "username":  user.username,
                "full_name": user.full_name,
                "role":      user.role.value,
            }
        )

    except ValueError as e:
        logger.error(f"Google Token Verification Failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid Google token")
    except RuntimeError as e:
        logger.error(f"Google Login Unavailable: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is temporarily unavailable",
        )

@router.post("/apple-login", response_model=TokenResponse)
<<<<<<< HEAD
async def apple_login(body: AppleLoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    # Rate limit: 10 Apple login attempts per minute per IP
    rate_limiter.check(request, "apple-login", max_requests=10, window_seconds=60)

=======
async def apple_login(body: AppleLoginRequest, db: AsyncSession = Depends(get_db)):
>>>>>>> e8057c814e93e052b4b5426cd31920469f1aa1d3
    """
    Verifies an Apple Identity token, creates or identifies the user, and issues JWT tokens.
    """
    import logging
    import secrets
    import string
    import jwt  # requires PyJWT

    logger = logging.getLogger("uvicorn")
    if not settings.APPLE_BUNDLE_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Apple Sign-In is temporarily unavailable",
        )

    try:
        unverified_header = jwt.get_unverified_header(body.identity_token)
        kid = unverified_header.get("kid")
        if not kid:
            raise ValueError("Apple token header missing key id")
        public_key = get_apple_public_key(kid)
        if not public_key:
            raise ValueError("Apple signing key not found")

        claims = jwt.decode(
            body.identity_token,
            key=public_key,
            algorithms=["RS256"],
            audience=settings.APPLE_BUNDLE_ID,
            issuer="https://appleid.apple.com",
        )
        
        # Additional explicit validation of required claims
        if claims.get("iss") != "https://appleid.apple.com":
            raise ValueError("Invalid Apple token issuer")
        if claims.get("aud") != settings.APPLE_BUNDLE_ID:
            raise ValueError("Apple token audience mismatch")
        
        email = claims.get("email")
        apple_sub = claims.get("sub")
        if not apple_sub:
            raise ValueError("Apple token missing subject")

        email_norm = email.lower().strip() if email else None
        full_name = body.full_name or "Apple User"
        user = None
        
        # Try to find user by email first, then by apple_sub as fallback
        if email_norm:
            result = await db.execute(select(User).where(User.email == email_norm))
            user = result.scalar_one_or_none()
        if not user:
            # Fallback to sub claim lookup when email is absent or not found
            result = await db.execute(select(User).where(User.username == f"apple_{apple_sub}"))
            user = result.scalar_one_or_none()

        if not user:
            logger.info(f"✨ Creating new Apple account for {email_norm or apple_sub}")
            username = f"apple_{apple_sub}" if apple_sub else f"apple_{secrets.token_hex(4)}"
            random_pw = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
            generated_email = email_norm or f"{username}@privaterelay.appleid.com"
            user = User(
                email         = generated_email,
                username      = username,
                password_hash = hash_password(random_pw),
                full_name     = full_name,
                is_active     = True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        else:
            if not user.is_active:
                raise HTTPException(status_code=403, detail="Account disabled")
            logger.info(f"🔑 Apple login for existing user: {user.email}")

        # Issue standard tokens
        access_token  = create_access_token({"sub": str(user.id), "role": user.role.value})
        refresh_token = create_refresh_token({"sub": str(user.id)})

        token_hash = sha256(refresh_token.encode()).hexdigest()
        db.add(RefreshToken(
            user_id    = user.id,
            token_hash = token_hash,
            expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        ))
        await db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user={
                "id":        user.id,
                "email":     user.email,
                "username":  user.username,
                "full_name": user.full_name,
                "role":      user.role.value,
            }
        )

    except Exception as e:
        logger.error(f"Apple Token Verification Failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid Apple token")


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id":         current_user.id,
        "email":      current_user.email,
        "username":   current_user.username,
        "full_name":  current_user.full_name,
        "role":       current_user.role.value,
        "created_at": current_user.created_at.isoformat(),
    }


@router.patch("/me")
async def update_me(
    body: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession   = Depends(get_db),
):
    if body.full_name is not None:
        current_user.full_name = body.full_name
    
    if body.email is not None and body.email != current_user.email:
        # Check uniqueness
        result = await db.execute(select(User).where(User.email == body.email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already taken")
        current_user.email = body.email

    await db.commit()
    await db.refresh(current_user)
    return {
        "success": True, 
        "message": "Profile updated",
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "username": current_user.username,
            "full_name": current_user.full_name,
            "role": current_user.role.value,
        }
    }


@router.patch("/me/password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession   = Depends(get_db),
):
    if not verify_password(body.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Old password is incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

    current_user.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"success": True, "message": "Password updated"}


# ── Forgot / Reset Password ────────────────────────────────────────────────────

@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """
    Always returns 200 (prevents email enumeration).
    If user exists, generates a short-lived reset JWT and emails it.
    In dev mode (no SMTP creds), prints the link to the server console.
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user   = result.scalar_one_or_none()

    if user and user.is_active:
        from jose import jwt as jose_jwt
        expire     = datetime.now(timezone.utc) + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES)
        payload    = {"sub": str(user.id), "type": "reset", "exp": expire}
        reset_token = jose_jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        reset_url   = f"{settings.FRONTEND_RESET_URL}?token={reset_token}"

        send_password_reset_email(
            to_email=user.email,
            to_name=user.full_name or user.username,
            reset_url=reset_url,
        )

    return {
        "success": True,
        "message": "If that email is registered, a reset link has been sent.",
    }


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Verifies the JWT reset token and updates the user's password."""
    from jose import jwt as jose_jwt, JWTError

    try:
        payload = jose_jwt.decode(body.token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=400, detail="Reset link is invalid or has expired.")

    if payload.get("type") != "reset":
        raise HTTPException(status_code=400, detail="Invalid token type.")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid token payload.")

    # [Harden] Single-use check: ensure token hash is not in UsedResetToken
    from app.models.user import UsedResetToken
    token_hash = sha256(body.token.encode()).hexdigest()
    result = await db.execute(select(UsedResetToken).where(UsedResetToken.token_hash == token_hash))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="This reset link has already been used.")

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user   = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found.")

    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    user.password_hash = hash_password(body.new_password)
    
    # [Harden] Mark token as used
    db.add(UsedResetToken(token_hash=token_hash))
    
    await db.commit()
    return {"success": True, "message": "Password has been reset. Please sign in."}
