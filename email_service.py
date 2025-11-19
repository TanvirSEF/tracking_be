import aiosmtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from datetime import datetime, timedelta
import secrets
import string

from config import settings
import models

class EmailService:
    """Professional email service for sending emails"""
    
    def __init__(self):
        self.smtp_host = settings.EMAIL_SMTP_HOST
        self.smtp_port = settings.EMAIL_SMTP_PORT
        self.smtp_username = settings.EMAIL_SMTP_USERNAME
        self.smtp_password = settings.EMAIL_SMTP_PASSWORD
        self.from_name = settings.EMAIL_FROM_NAME
        self.from_email = settings.EMAIL_FROM_EMAIL or settings.EMAIL_SMTP_USERNAME
    
    def _is_configured(self) -> bool:
        """Check if email service is properly configured"""
        if not self.smtp_host or not self.smtp_port:
            return False
        if not self.smtp_username or not self.smtp_password:
            return False
        # from_email can fallback to smtp_username, so check if at least one is set
        if not self.from_email and not self.smtp_username:
            return False
        return True
    
    async def _create_smtp_connection(self):
        """Create secure async SMTP connection"""
        if not self._is_configured():
            raise ValueError("Email service is not properly configured. Please check your .env file for EMAIL_SMTP_* settings.")
        
        context = ssl.create_default_context()
        server = aiosmtplib.SMTP(
            hostname=self.smtp_host,
            port=self.smtp_port,
            use_tls=True,
            tls_context=context
        )
        
        await server.connect()
        
        if self.smtp_username and self.smtp_password:
            await server.login(self.smtp_username, self.smtp_password)
        
        return server
    
    async def send_welcome_email(self, to_email: str, user_type: str, name: str = None) -> bool:
        """Send welcome email after registration"""
        # Check if email service is configured
        if not self._is_configured():
            print(f"ERROR: Cannot send welcome email to {to_email} - Email service not configured")
            print("Please set EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, EMAIL_SMTP_USERNAME, EMAIL_SMTP_PASSWORD, and EMAIL_FROM_EMAIL in your .env file")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Welcome to OneMove Affiliate Management System"
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            display_name = name or to_email.split('@')[0]
            
            # HTML welcome email
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Welcome</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                        background-color: #f4f4f4;
                    }}
                    .container {{
                        background-color: #ffffff;
                        padding: 30px;
                        border-radius: 10px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    }}
                    .header {{
                        text-align: center;
                        margin-bottom: 30px;
                    }}
                    .logo {{
                        font-size: 24px;
                        font-weight: bold;
                        color: #27ae60;
                        margin-bottom: 10px;
                    }}
                    .success {{
                        background-color: #d4edda;
                        border: 1px solid #c3e6cb;
                        color: #155724;
                        padding: 15px;
                        border-radius: 5px;
                        margin: 20px 0;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="logo">✅ Welcome to <span class="onemove-brand">OneMove</span> Affiliate Management System</div>
                    </div>
                    
                    <div class="success">
                        <strong>🎉 Congratulations!</strong> Your {user_type} account has been successfully created.
                    </div>
                    
                    <p>Hello {display_name},</p>
                    <p>Welcome to the Affiliate Management System! Your account is now active.</p>
                    
                    <p>You can now:</p>
                    <ul>
                        <li>Log in to your account</li>
                        <li>Access all system features</li>
                        <li>Manage your profile</li>
                    </ul>
                    
                    <p>If you have any questions, please don't hesitate to contact our support team.</p>
                    
                    <p>Best regards,<br>Affiliate Management System Team</p>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
            Welcome to OneMove Affiliate Management System
            
            Hello {display_name},
            
            Congratulations! Your {user_type} account has been successfully created.
            
            Your account is now active.
            
            You can now:
            - Log in to your account
            - Access all system features
            - Manage your profile
            
            If you have any questions, please don't hesitate to contact our support team.
            
            Best regards,
            OneMove Affiliate Management System Team
            """
            
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email using async SMTP
            server = await self._create_smtp_connection()
            try:
                await server.send_message(msg)
                print(f"✓ Welcome email sent successfully to {to_email}")
                return True
            finally:
                await server.quit()
            
        except ValueError as e:
            # Configuration error
            print(f"ERROR: {e}")
            return False
        except Exception as e:
            print(f"ERROR: Failed to send welcome email to {to_email}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def send_password_reset_email(self, to_email: str, reset_token: str) -> bool:
        """Send password reset email with professional template"""
        # Check if email service is configured
        if not self._is_configured():
            print(f"ERROR: Cannot send password reset email to {to_email} - Email service not configured")
            print("Please set EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, EMAIL_SMTP_USERNAME, EMAIL_SMTP_PASSWORD, and EMAIL_FROM_EMAIL in your .env file")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = "OneMove Password Reset Request"
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Create reset URL (you can customize this based on your frontend)
            reset_url = f"{settings.RESET_PASSWORD_URL}?token={reset_token}"
            
            # HTML password reset email
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Password Reset Request</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                        background-color: #f4f4f4;
                    }}
                    .container {{
                        background-color: #ffffff;
                        padding: 30px;
                        border-radius: 10px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    }}
                    .header {{
                        text-align: center;
                        margin-bottom: 30px;
                    }}
                    .logo {{
                        font-size: 24px;
                        font-weight: bold;
                        color: #2c3e50;
                        margin-bottom: 10px;
                    }}
                    .onemove-brand {{
                        color: #007bff;
                        font-weight: bold;
                    }}
                    .title {{
                        font-size: 20px;
                        color: #2c3e50;
                        margin-bottom: 20px;
                    }}
                    .content {{
                        margin-bottom: 30px;
                    }}
                    .button {{
                        display: inline-block;
                        background-color: #dc3545;
                        color: white;
                        padding: 12px 30px;
                        text-decoration: none;
                        border-radius: 5px;
                        font-weight: bold;
                        margin: 20px 0;
                    }}
                    .button:hover {{
                        background-color: #c82333;
                    }}
                    .footer {{
                        margin-top: 30px;
                        padding-top: 20px;
                        border-top: 1px solid #eee;
                        font-size: 12px;
                        color: #666;
                        text-align: center;
                    }}
                    .warning {{
                        background-color: #fff3cd;
                        border: 1px solid #ffeaa7;
                        color: #856404;
                        padding: 15px;
                        border-radius: 5px;
                        margin: 20px 0;
                    }}
                    .token-display {{
                        background-color: #f8f9fa;
                        border: 2px solid #dc3545;
                        border-radius: 10px;
                        padding: 20px;
                        text-align: center;
                        font-size: 18px;
                        font-weight: bold;
                        letter-spacing: 3px;
                        color: #dc3545;
                        font-family: 'Courier New', monospace;
                        margin: 20px 0;
                        word-break: break-all;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="logo">🔐 <span class="onemove-brand">OneMove</span> Password Reset</div>
                        <div class="title">Password Reset Request</div>
                    </div>
                    
                    <div class="content">
                        <p>Hello,</p>
                        <p>We received a request to reset your password for your OneMove account.</p>
                        
                        <p>To reset your password, please use the following reset token:</p>
                        
                        <div class="token-display">
                            {reset_token}
                        </div>
                        
                        <p>Or click the button below to reset your password:</p>
                        
                        <div style="text-align: center;">
                            <a href="{reset_url}" class="button">Reset My Password</a>
                        </div>
                        
                        <div class="warning">
                            <strong>⚠️ Important Security Information:</strong>
                            <ul>
                                <li>This reset token will expire in 24 hours</li>
                                <li>This token can only be used once</li>
                                <li>If you didn't request this reset, please ignore this email</li>
                                <li>Your password will remain unchanged until you use this token</li>
                            </ul>
                        </div>
                        
                        <p>If you have any questions or concerns, please contact our support team immediately.</p>
                    </div>
                    
                    <div class="footer">
                        <p>This email was sent by the <strong>OneMove Affiliate Management System</strong>.</p>
                        <p>If you didn't request this password reset, please ignore this email and your password will remain unchanged.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Plain text version
            text_content = f"""
            OneMove Password Reset Request
            
            Hello,
            
            We received a request to reset your password for your OneMove account.
            
            To reset your password, please use the following reset token:
            
            {reset_token}
            
            Or visit this link: {reset_url}
            
            IMPORTANT SECURITY INFORMATION:
            - This reset token will expire in 24 hours
            - This token can only be used once
            - If you didn't request this reset, please ignore this email
            - Your password will remain unchanged until you use this token
            
            If you have any questions or concerns, please contact our support team immediately.
            
            This email was sent by the OneMove Affiliate Management System.
            If you didn't request this password reset, please ignore this email and your password will remain unchanged.
            """
            
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email using async SMTP
            server = await self._create_smtp_connection()
            try:
                await server.send_message(msg)
                print(f"✓ Password reset email sent successfully to {to_email}")
                return True
            finally:
                await server.quit()
            
        except ValueError as e:
            # Configuration error
            print(f"ERROR: {e}")
            return False
        except Exception as e:
            print(f"ERROR: Failed to send password reset email to {to_email}: {e}")
            import traceback
            traceback.print_exc()
            return False

# Global email service instance
email_service = EmailService()
