import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

class GoogleConfig:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

class GoogleAPIClient:
    # Scopes needed: Gmail send, Gmail read (for reply tracking), Userinfo email/profile
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile',
        'openid'
    ]

    def _generate_pkce(self) -> Tuple[str, str]:
        """Generate PKCE code_verifier and code_challenge."""
        import secrets
        import hashlib
        import base64
        
        # 1. Create code_verifier
        verifier = secrets.token_urlsafe(32)
        
        # 2. Create code_challenge
        challenge_hash = hashlib.sha256(verifier.encode('ascii')).digest()
        challenge = base64.urlsafe_b64encode(challenge_hash).decode('ascii').replace('=', '')
        
        return verifier, challenge

    def get_auth_url(self, config: GoogleConfig, state_prefix: str) -> str:
        """Generate Google OAuth authorization URL with manual PKCE."""
        import urllib.parse
        
        verifier, challenge = self._generate_pkce()
        
        # Append verifier to state so we can recover it in the callback
        # State format: prefix:verifier
        state = f"{state_prefix}:{verifier}"
        
        params = {
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.SCOPES),
            "state": state,
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "code_challenge": challenge,
            "code_challenge_method": "S256"
        }
        
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        return f"{base_url}?{urllib.parse.urlencode(params)}"

    def fetch_token(self, config: GoogleConfig, code: str, code_verifier: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens using manual PKCE verifier."""
        import requests
        
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "redirect_uri": config.redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": code_verifier
        }
        
        response = requests.post(token_url, data=data)
        if not response.ok:
            raise Exception(f"Failed to fetch token: {response.text}")
            
        token_data = response.json()
        expires_in = token_data.get("expires_in", 3600)
        expiry = datetime.utcnow() + timedelta(seconds=expires_in)
        
        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "scopes": self.SCOPES,
            "expires_at": expiry
        }

    def get_user_info(self, credentials_dict: Dict[str, Any]) -> Tuple[str, str]:
        """Get user email and name using tokens."""
        creds = Credentials(
            token=credentials_dict['access_token'],
            refresh_token=credentials_dict.get('refresh_token'),
            token_uri=credentials_dict.get('token_uri', "https://oauth2.googleapis.com/token"),
            client_id=credentials_dict.get('client_id'),
            client_secret=credentials_dict.get('client_secret'),
            scopes=credentials_dict.get('scopes')
        )
        
        service = build('oauth2', 'v2', credentials=creds)
        user_info = service.userinfo().get().execute()
        
        return user_info.get('email'), user_info.get('name', '')

    def send_email(self, credentials_dict: Dict[str, Any], to: str, subject: str, body: str, html: Optional[str] = None) -> bool:
        """Send email via Gmail API."""
        import base64
        from email.message import EmailMessage
        
        creds = Credentials(
            token=credentials_dict['access_token'],
            refresh_token=credentials_dict.get('refresh_token'),
            token_uri=credentials_dict.get('token_uri', "https://oauth2.googleapis.com/token"),
            client_id=credentials_dict.get('client_id'),
            client_secret=credentials_dict.get('client_secret'),
            scopes=credentials_dict.get('scopes')
        )
        
        service = build('gmail', 'v1', credentials=creds)
        
        message = EmailMessage()
        message.set_content(body)
        if html:
            message.add_alternative(html, subtype='html')
            
        message['To'] = to
        message['Subject'] = subject
        
        # encoded message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        create_message = {
            'raw': encoded_message
        }
        
        send_message = (service.users().messages().send(userId="me", body=create_message).execute())
        return 'id' in send_message
