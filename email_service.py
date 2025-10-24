import smtplib
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
    """Professional email service for sending verification emails"""
    
    def __init__(self):
        self.smtp_host = settings.EMAIL_SMTP_HOST
        self.smtp_port = settings.EMAIL_SMTP_PORT
        self.smtp_username = settings.EMAIL_SMTP_USERNAME
        self.smtp_password = settings.EMAIL_SMTP_PASSWORD
        self.from_name = settings.EMAIL_FROM_NAME
        self.from_email = settings.EMAIL_FROM_EMAIL or settings.EMAIL_SMTP_USERNAME
    
    def _create_smtp_connection(self):
        """Create secure SMTP connection"""
        context = ssl.create_default_context()
        server = smtplib.SMTP(self.smtp_host, self.smtp_port)
        server.starttls(context=context)
        
        if self.smtp_username and self.smtp_password:
            server.login(self.smtp_username, self.smtp_password)
        
        return server
    
    def _create_verification_email(self, to_email: str, verification_code: str, user_type: str) -> MIMEMultipart:
        """Create professional verification email"""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"OneMove {user_type.title()} Account Verification"
        msg['From'] = f"{self.from_name} <{self.from_email}>"
        msg['To'] = to_email
        
        # Email content
        if user_type == "admin":
            title = "OneMove Admin Account Verification"
            description = "Please verify your OneMove admin account to complete the registration process."
        elif user_type == "affiliate":
            title = "OneMove Affiliate Account Verification"
            description = "Please verify your OneMove affiliate account to complete the registration process."
        else:
            title = "OneMove Account Verification"
            description = "Please verify your OneMove account to complete the registration process."
        
        # HTML email template
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
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
                    background-color: #3498db;
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    margin: 20px 0;
                }}
                .button:hover {{
                    background-color: #2980b9;
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
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🏢 <span class="onemove-brand">OneMove</span> Affiliate Management System</div>
                    <div class="title">{title}</div>
                </div>
                
                <div class="content">
                    <p>Hello,</p>
                    <p>{description}</p>
                    
                    <p>Your <strong>OneMove verification code</strong> is:</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <div style="background-color: #f8f9fa; border: 2px solid #007bff; border-radius: 10px; padding: 20px; display: inline-block; font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #007bff; font-family: 'Courier New', monospace;">
                            {verification_code}
                        </div>
                    </div>
                    
                    <div class="warning">
                        <strong>⚠️ Important:</strong> This verification code will expire in 24 hours for security reasons.
                    </div>
                    
                    <p>Enter this code in the verification form to complete your registration.</p>
                </div>
                
                <div class="footer">
                    <p>This email was sent by the <strong>OneMove Affiliate Management System</strong>.</p>
                    <p>If you didn't request this verification, please ignore this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        text_content = f"""
        {title}
        
        Hello,
        
        {description}
        
        Your OneMove verification code is: {verification_code}
        
        This verification code will expire in 24 hours for security reasons.
        
        Enter this code in the verification form to complete your registration.
        
        If you didn't request this verification, please ignore this email.
        
        Best regards,
        OneMove Affiliate Management System
        """
        
        # Attach parts
        text_part = MIMEText(text_content, 'plain')
        html_part = MIMEText(html_content, 'html')
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        return msg
    
    async def send_verification_email(self, to_email: str, code: str, user_type: str) -> bool:
        """Send verification email with professional template"""
        try:
            # Create email message with verification code
            msg = self._create_verification_email(to_email, code, user_type)
            
            # Send email
            with self._create_smtp_connection() as server:
                server.send_message(msg)
            
            print(f"Verification email sent to {to_email}")
            return True
            
        except Exception as e:
            print(f"Failed to send verification email to {to_email}: {e}")
            return False
    
    async def send_welcome_email(self, to_email: str, user_type: str, name: str = None) -> bool:
        """Send welcome email after successful verification"""
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
                        <strong>🎉 Congratulations!</strong> Your {user_type} account has been successfully verified.
                    </div>
                    
                    <p>Hello {display_name},</p>
                    <p>Welcome to the Affiliate Management System! Your email has been verified and your account is now active.</p>
                    
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
            
            Congratulations! Your {user_type} account has been successfully verified.
            
            Your email has been verified and your account is now active.
            
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
            
            # Send email
            with self._create_smtp_connection() as server:
                server.send_message(msg)
            
            print(f"Welcome email sent to {to_email}")
            return True
            
        except Exception as e:
            print(f"Failed to send welcome email to {to_email}: {e}")
            return False

# Global email service instance
email_service = EmailService()
