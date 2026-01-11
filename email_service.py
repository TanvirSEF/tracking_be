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
        
        # For port 587, use STARTTLS (connect first, then upgrade)
        # For port 465, use direct TLS (use_tls=True)
        if self.smtp_port == 587:
            # Port 587 uses STARTTLS - aiosmtplib handles this automatically
            server = aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
                use_tls=False,  # Don't use direct TLS
                start_tls=True,  # Use STARTTLS instead
                tls_context=context
            )
            await server.connect()
        else:
            # Port 465 or other ports use direct TLS
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
                print(f"[SUCCESS] Welcome email sent successfully to {to_email}")
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
                        padding: 40px;
                        border-radius: 10px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    }}
                    .content {{
                        text-align: center;
                        margin-bottom: 30px;
                    }}
                    .button {{
                        display: inline-block;
                        background-color: #c4a572;
                        color: #ffffff !important;
                        padding: 14px 40px;
                        text-decoration: none !important;
                        border-radius: 5px;
                        font-weight: bold;
                        font-size: 16px;
                        margin: 30px 0;
                        border: none;
                    }}
                    .button:hover {{
                        background-color: #b89562;
                        color: #ffffff !important;
                    }}
                    a.button {{
                        color: #ffffff !important;
                        text-decoration: none !important;
                    }}
                    .footer {{
                        margin-top: 30px;
                        padding-top: 20px;
                        border-top: 1px solid #eee;
                        font-size: 12px;
                        color: #666;
                        text-align: center;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="content">
                        <p>Hello,</p>
                        <p>We received a request to reset your password for your OneMove account.</p>
                        <p>Click the button below to reset your password:</p>
                        
                        <div>
                            <a href="{reset_url}" class="button" style="background-color: #c4a572; color: #ffffff !important; text-decoration: none; padding: 14px 40px; border-radius: 5px; font-weight: bold; font-size: 16px; display: inline-block;">Reset My Password</a>
                        </div>
                        
                        <p style="font-size: 12px; color: #666; margin-top: 30px;">
                            This link will expire in 24 hours. If you didn't request this reset, please ignore this email.
                        </p>
                    </div>
                    
                    <div class="footer">
                        <p>This email was sent by the <strong>OneMove Affiliate Management System</strong>.</p>
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
            
            To reset your password, please visit this link:
            {reset_url}
            
            This link will expire in 24 hours. If you didn't request this reset, please ignore this email.
            
            This email was sent by the OneMove Affiliate Management System.
            """
            
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email using async SMTP
            server = await self._create_smtp_connection()
            try:
                await server.send_message(msg)
                print(f"[SUCCESS] Password reset email sent successfully to {to_email}")
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
    
    async def send_custom_email(self, to_email: str, subject: str, message: str, recipient_name: str = None) -> bool:
        """Send custom email with HTML content"""
        # Check if email service is configured
        if not self._is_configured():
            print(f"ERROR: Cannot send custom email to {to_email} - Email service not configured")
            print("Please set EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, EMAIL_SMTP_USERNAME, EMAIL_SMTP_PASSWORD, and EMAIL_FROM_EMAIL in your .env file")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            display_name = recipient_name or to_email.split('@')[0]
            
            # HTML email template with custom message
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{subject}</title>
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
                    .content {{
                        margin: 20px 0;
                    }}
                    .footer {{
                        margin-top: 30px;
                        padding-top: 20px;
                        border-top: 1px solid #eee;
                        font-size: 12px;
                        color: #666;
                        text-align: center;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="logo">OneMove Affiliate Management System</div>
                    </div>
                    
                    <div class="content">
                        <p>Hello {display_name},</p>
                        {message}
                    </div>
                    
                    <div class="footer">
                        <p>This email was sent by your affiliate from the <strong>OneMove Affiliate Management System</strong>.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Plain text version (strip HTML tags for basic text)
            import re
            text_content = re.sub(r'<[^>]+>', '', message)
            text_content = f"""
            {subject}
            
            Hello {display_name},
            
            {text_content}
            
            ---
            This email was sent by your affiliate from the OneMove Affiliate Management System.
            """
            
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email using async SMTP
            server = await self._create_smtp_connection()
            try:
                await server.send_message(msg)
                print(f"[SUCCESS] Custom email sent successfully to {to_email}")
                return True
            finally:
                await server.quit()
            
        except ValueError as e:
            # Configuration error
            print(f"ERROR: {e}")
            return False
        except Exception as e:
            print(f"ERROR: Failed to send custom email to {to_email}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def send_affiliate_template_email(
        self,
        to_email: str,
        affiliate_template: dict,
        member_name: str,
        member_email: str,
        affiliate_name: str,
        affiliate_email: str,
        unique_link: str,
        registration_date: str
    ) -> bool:
        """Send email using affiliate's custom template with variable substitution"""
        # Check if email service is configured
        if not self._is_configured():
            print(f"ERROR: Cannot send template email to {to_email} - Email service not configured")
            return False
        
        try:
            # Variable substitution mapping
            variables = {
                '{member_name}': member_name,
                '{member_email}': member_email,
                '{affiliate_name}': affiliate_name,
                '{affiliate_email}': affiliate_email,
                '{unique_link}': unique_link,
                '{registration_date}': registration_date
            }
            
            # Substitute variables in subject and content
            subject = affiliate_template['subject']
            html_content = affiliate_template['html_content']
            text_content = affiliate_template.get('text_content', '')
            
            for var, value in variables.items():
                subject = subject.replace(var, value)
                html_content = html_content.replace(var, value)
                if text_content:
                    text_content = text_content.replace(var, value)
            
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # If no text content provided, create basic text version from HTML
            if not text_content:
                import re
                text_content = re.sub(r'<[^>]+>', '', html_content)
            
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            server = await self._create_smtp_connection()
            try:
                await server.send_message(msg)
                print(f"[SUCCESS] Affiliate template email sent successfully to {to_email}")
                return True
            finally:
                await server.quit()
        
        except ValueError as e:
            print(f"ERROR: {e}")
            return False
        except Exception as e:
            print(f"ERROR: Failed to send affiliate template email to {to_email}: {e}")
            import traceback
            traceback.print_exc()
            return False

# Global email service instance
email_service = EmailService()
