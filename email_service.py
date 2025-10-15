import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import secrets
import string
from datetime import datetime, timedelta

from config import settings

class EmailService:
    """Simple email service for sending verification codes"""
    
    @staticmethod
    def generate_verification_code() -> str:
        """Generate a 6-digit verification code"""
        return ''.join(secrets.choice(string.digits) for _ in range(6))
    
    @staticmethod
    async def send_verification_email(email: str, verification_code: str) -> bool:
        """Send verification code email"""
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = "Email Verification - 1move Community"
            message["From"] = f"{settings.FROM_NAME} <{settings.FROM_EMAIL}>"
            message["To"] = email
            
            # Create HTML content
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50;">Email Verification</h2>
                    <p>Hello,</p>
                    <p>Thank you for registering with 1move Community. Please use the verification code below to verify your email address:</p>
                    
                    <div style="background-color: #f8f9fa; border: 2px solid #e9ecef; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0;">
                        <h1 style="color: #007bff; font-size: 32px; margin: 0; letter-spacing: 5px;">{verification_code}</h1>
                    </div>
                    
                    <p>This code will expire in 15 minutes.</p>
                    <p>If you didn't request this verification, please ignore this email.</p>
                    
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="color: #666; font-size: 14px;">
                        Best regards,<br>
                        The 1move Community Team
                    </p>
                </div>
            </body>
            </html>
            """
            
            # Create plain text content
            text_content = f"""
            Email Verification - 1move Community
            
            Hello,
            
            Thank you for registering with 1move Community. Please use the verification code below to verify your email address:
            
            Verification Code: {verification_code}
            
            This code will expire in 15 minutes.
            
            If you didn't request this verification, please ignore this email.
            
            Best regards,
            The 1move Community Team
            """
            
            # Attach parts
            text_part = MIMEText(text_content, "plain")
            html_part = MIMEText(html_content, "html")
            
            message.attach(text_part)
            message.attach(html_part)
            
            # Send email
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                use_tls=settings.SMTP_USE_TLS,
                username=settings.SMTP_USERNAME,
                password=settings.SMTP_PASSWORD,
            )
            
            return True
            
        except Exception as e:
            print(f"Failed to send email to {email}: {e}")
            return False
    
    @staticmethod
    def get_verification_expiry() -> datetime:
        """Get verification code expiry time (15 minutes from now)"""
        return datetime.utcnow() + timedelta(minutes=15)
