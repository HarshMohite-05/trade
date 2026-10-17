from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional
from ..config import current_settings, save_settings
from ..core.upstox_service import upstox_service

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class CredentialsRequest(BaseModel):
    api_key: str
    api_secret: str
    redirect_uri: Optional[str] = "http://localhost:8000/api/auth/callback"

class TokenRequest(BaseModel):
    access_token: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None

class CodeExchangeRequest(BaseModel):
    code: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    redirect_uri: Optional[str] = None

@router.get("/status")
def get_auth_status():
    is_authenticated = bool(current_settings.access_token)
    token_preview = None
    if is_authenticated and current_settings.access_token:
        tok = current_settings.access_token
        token_preview = f"{tok[:6]}...{tok[-4:]}" if len(tok) > 10 else "***"
        
    return {
        "authenticated": is_authenticated,
        "api_key": current_settings.api_key or "",
        "redirect_uri": current_settings.redirect_uri or "",
        "token_preview": token_preview,
        "user_name": current_settings.user_name,
        "user_id": current_settings.user_id,
    }

@router.post("/credentials")
def save_credentials(req: CredentialsRequest):
    current_settings.api_key = req.api_key.strip()
    current_settings.api_secret = req.api_secret.strip()
    if req.redirect_uri:
        current_settings.redirect_uri = req.redirect_uri.strip()
    save_settings(current_settings)
    return {
        "status": "success",
        "message": "Credentials saved successfully",
        "login_url": upstox_service.get_auth_url()
    }

@router.get("/login-url")
def get_login_url():
    if not current_settings.api_key:
        raise HTTPException(status_code=400, detail="API Key is not configured yet. Please enter API Key & Secret.")
    url = upstox_service.get_auth_url()
    return {"url": url}

@router.post("/manual-token")
def set_manual_token(req: TokenRequest):
    res = upstox_service.set_manual_token(req.access_token, req.api_key, req.api_secret)
    return res

@router.post("/exchange-code")
def exchange_code(req: CodeExchangeRequest):
    api_key = req.api_key or current_settings.api_key
    api_secret = req.api_secret or current_settings.api_secret
    redirect_uri = req.redirect_uri or current_settings.redirect_uri

    if not api_key or not api_secret:
        raise HTTPException(status_code=400, detail="API Key and API Secret are required for token exchange.")

    res = upstox_service.exchange_code_for_token(
        code=req.code,
        api_key=api_key,
        api_secret=api_secret,
        redirect_uri=redirect_uri
    )
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message", "Token exchange failed"))
    return res

@router.get("/callback")
def auth_callback(code: Optional[str] = Query(None), error: Optional[str] = Query(None)):
    """
    OAuth redirect endpoint. Exchanges code and renders a success message or redirects to frontend.
    """
    if error:
        return HTMLResponse(
            f"<html><body style='background:#0b0e14;color:#ef4444;font-family:sans-serif;padding:40px;'>"
            f"<h2>Authentication Error</h2><p>{error}</p>"
            f"<a href='http://localhost:5173' style='color:#3b82f6;'>Return to Dashboard</a></body></html>"
        )
    if not code:
        return HTMLResponse(
            "<html><body style='background:#0b0e14;color:#ef4444;font-family:sans-serif;padding:40px;'>"
            "<h2>Missing authorization code</h2></body></html>"
        )
    
    res = upstox_service.exchange_code_for_token(
        code=code,
        api_key=current_settings.api_key,
        api_secret=current_settings.api_secret,
        redirect_uri=current_settings.redirect_uri
    )
    
    if res.get("status") == "success":
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <title>Upstox Connected</title>
          <meta http-equiv="refresh" content="2;url=http://localhost:5173" />
          <style>
            body {{ background: #0b0e14; color: #10b981; font-family: system-ui, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
            .card {{ background: #161b26; border: 1px solid #232a3b; padding: 32px; border-radius: 12px; text-align: center; max-width: 400px; }}
            h2 {{ margin-top: 0; }}
            p {{ color: #94a3b8; font-size: 14px; }}
            a {{ color: #3b82f6; text-decoration: none; }}
          </style>
        </head>
        <body>
          <div class="card">
            <h2>Authentication Successful!</h2>
            <p>Connected as <strong>{current_settings.user_name or current_settings.user_id}</strong></p>
            <p>Redirecting to dashboard in 2 seconds...</p>
            <a href="http://localhost:5173">Click here if not redirected automatically</a>
          </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html)
    else:
        return HTMLResponse(
            f"<html><body style='background:#0b0e14;color:#ef4444;font-family:sans-serif;padding:40px;'>"
            f"<h2>Token Exchange Failed</h2><p>{res.get('message')}</p>"
            f"<a href='http://localhost:5173' style='color:#3b82f6;'>Return to Dashboard</a></body></html>"
        )

@router.post("/logout")
def logout():
    current_settings.access_token = None
    current_settings.user_name = None
    current_settings.user_id = None
    save_settings(current_settings)
    return {"status": "success", "message": "Logged out successfully"}
