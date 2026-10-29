"""Supabase authentication, kept separate from the existing task application."""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, SecretStr
from supabase import ClientOptions, create_client
from supabase_auth.errors import AuthApiError

load_dotenv(Path(__file__).with_name('.env'))
router = APIRouter(tags=['Authentication'])


def get_auth():
    """A fresh client per request prevents one user's session leaking to another."""
    url, key = os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY')
    if not url or not key:
        raise HTTPException(503, 'Configure SUPABASE_URL and SUPABASE_KEY in .env')
    return create_client(url, key, options=ClientOptions(
        persist_session=False, auto_refresh_token=False)).auth


class Credentials(BaseModel):
    email: str = Field(min_length=1)
    password: SecretStr = Field(min_length=1)

    def payload(self):
        email = self.email.strip()
        password = self.password.get_secret_value()
        if not email or not password.strip():
            raise HTTPException(400, 'Email and password are required')
        return {'email': email, 'password': password}


def safe_user(user):
    return {'id': user.id, 'email': user.email, 'created_at': user.created_at}


@router.post('/auth/signup', status_code=201)
def signup(data: Credentials, auth=Depends(get_auth)):
    try:
        result = auth.sign_up(data.payload())
    except AuthApiError:
        raise HTTPException(400, 'Unable to sign up. Check your details and email confirmation.') from None
    except httpx.HTTPError:
        raise HTTPException(503, 'Authentication service unavailable') from None
    if not result.user:
        raise HTTPException(400, 'Unable to sign up')
    return safe_user(result.user)


@router.post('/auth/login')
def login(data: Credentials, response: Response, auth=Depends(get_auth)):
    try:
        result = auth.sign_in_with_password(data.payload())
    except AuthApiError:
        raise HTTPException(401, 'Invalid login credentials') from None
    except httpx.HTTPError:
        raise HTTPException(503, 'Authentication service unavailable') from None
    if not result.session:
        raise HTTPException(401, 'Invalid login credentials')
    response.headers['Cache-Control'] = 'no-store'
    return {'access_token': result.session.access_token,
            'refresh_token': result.session.refresh_token, 'token_type': 'bearer'}


bearer = HTTPBearer(auto_error=False, bearerFormat='JWT')


@dataclass
class VerifiedUser:
    user: Any
    token: str
    auth: Any


def extract_token(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    if credentials is None or len(credentials.credentials.split()) != 1:
        raise HTTPException(401, 'Access token required', headers={'WWW-Authenticate': 'Bearer'})
    return credentials.credentials


def require_user(token: Annotated[str, Depends(extract_token)], auth=Depends(get_auth)):
    try:
        result = auth.get_user(token)
    except AuthApiError:
        raise HTTPException(401, 'Invalid or expired token', headers={'WWW-Authenticate': 'Bearer'}) from None
    except httpx.HTTPError:
        raise HTTPException(503, 'Authentication service unavailable') from None
    if not result or not result.user:
        raise HTTPException(401, 'Invalid or expired token', headers={'WWW-Authenticate': 'Bearer'})
    return VerifiedUser(result.user, token, auth)


@router.get('/public/info', tags=['Public'])
def public_info():
    return {'message': 'Welcome stranger! This info is public.'}


@router.get('/protected/profile')
def profile(current: Annotated[VerifiedUser, Depends(require_user)]):
    return safe_user(current.user)


@router.get('/protected/dashboard')
def dashboard(current: Annotated[VerifiedUser, Depends(require_user)]):
    return {'message': 'Welcome to your protected dashboard.', 'user_id': current.user.id}


@router.post('/auth/logout', status_code=204)
def logout(current: Annotated[VerifiedUser, Depends(require_user)]):
    try:
        # Explicit caller JWT: never sign out a shared client's last logged-in user.
        current.auth.admin.sign_out(current.token, scope='local')
    except AuthApiError:
        raise HTTPException(401, 'Invalid or expired token') from None
    except httpx.HTTPError:
        raise HTTPException(503, 'Authentication service unavailable') from None
    return Response(status_code=204)
