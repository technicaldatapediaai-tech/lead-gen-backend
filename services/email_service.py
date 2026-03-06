"""
Email service - handles sending emails.
Currently supports: Mock (development) and SMTP (production ready).
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from abc import ABC, abstractmethod
from datetime import datetime

from backend.config import settings


class EmailService(ABC):
    """Base email service interface."""
    
    @abstractmethod
    async def send_email(
        self, 
        to: str, 
        subject: str, 
        body: str, 
        html: Optional[str] = None,
        from_email: Optional[str] = None,
        smtp_config: Optional[dict] = None
    ) -> bool:
        """Send an email."""
        pass
    
    async def send_verification_email(self, to: str, token: str, base_url: str) -> bool:
        """Send email verification email."""
        verify_link = f"{base_url}/verify-email?token={token}"
        
        subject = "Verify your Lead Genius account"
        body = f"Please verify your email: {verify_link}"
        html = f"<h2>Welcome!</h2><p><a href='{verify_link}'>Verify Email</a></p>"
        
        return await self.send_email(to, subject, body, html)
    
    async def send_password_reset_email(self, to: str, token: str, base_url: str) -> bool:
        """Send password reset email."""
        reset_link = f"{base_url}/reset-password?token={token}"
        
        subject = "Reset your password"
        body = f"Reset your password: {reset_link}"
        html = f"<h2>Password Reset</h2><p><a href='{reset_link}'>Reset Password</a></p>"
        
        return await self.send_email(to, subject, body, html)


class MockEmailService(EmailService):
    """
    Mock email service for development.
    Prints emails to console instead of sending.
    """
    
    sent_emails: list = []
    
    async def send_email(
        self, 
        to: str, 
        subject: str, 
        body: str, 
        html: Optional[str] = None,
        from_email: Optional[str] = None,
        smtp_config: Optional[dict] = None
    ) -> bool:
        """Mock send - prints to console."""
        print(f"\n📧 MOCK EMAIL to {to} (from {from_email or 'system'})")
        print(f"Subject: {subject}")
        if smtp_config:
            print(f"Using SMTP: {smtp_config.get('host')}")
        print("-" * 20)
        print(body[:200] + "..." if len(body) > 200 else body)
        print("-" * 20 + "\n")
        return True


class SMTPEmailService(EmailService):
    """
    SMTP email service for production.
    """
    
    def __init__(self):
        self.default_host = getattr(settings, 'SMTP_HOST', 'smtp.gmail.com')
        self.default_port = getattr(settings, 'SMTP_PORT', 587)
        self.default_user = getattr(settings, 'SMTP_USER', '')
        self.default_password = getattr(settings, 'SMTP_PASSWORD', '')
        self.default_from = getattr(settings, 'EMAIL_FROM', 'noreply@leadgenius.com')
    
    async def send_email(
        self, 
        to: str, 
        subject: str, 
        body: str, 
        html: Optional[str] = None,
        from_email: Optional[str] = None,
        smtp_config: Optional[dict] = None
    ) -> bool:
        """Send email via SMTP."""
        try:
            # Determine config to use
            host = (smtp_config.get('host') if smtp_config and smtp_config.get('host') else self.default_host)
            port = (smtp_config.get('port') if smtp_config and smtp_config.get('port') else self.default_port)
            user = (smtp_config.get('user') if smtp_config and smtp_config.get('user') else self.default_user)
            password = (smtp_config.get('password') if smtp_config and smtp_config.get('password') else self.default_password)
            from_addr = from_email or self.default_from
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = from_addr
            msg['To'] = to
            
            part1 = MIMEText(body, 'plain')
            msg.attach(part1)
            
            if html:
                part2 = MIMEText(html, 'html')
                msg.attach(part2)
            
            # Send
            with smtplib.SMTP(host, port) as server:
                server.starttls()
                if user and password:
                    server.login(user, password)
                server.sendmail(from_addr, to, msg.as_string())
            
            return True
        except Exception as e:
            error_msg = f"❌ Failed to send email to {to}: {str(e)}"
            print(error_msg)
            # Log to a file we can easily check
            with open("email_errors.log", "a") as f:
                f.write(f"{datetime.utcnow()} - {error_msg}\n")
            return False


_email_service: Optional[EmailService] = None

def get_email_service() -> EmailService:
    """Get the email service instance."""
    global _email_service
    if _email_service is None:
        smtp_host = getattr(settings, 'SMTP_HOST', None)
        if smtp_host or os.getenv('SMTP_HOST'):
            _email_service = SMTPEmailService()
        else:
            _email_service = MockEmailService()
    return _email_service


def set_email_service(service: EmailService) -> None:
    """Set custom email service (for testing)."""
    global _email_service
    _email_service = service
