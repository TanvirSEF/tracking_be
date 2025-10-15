import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging
from config import settings

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_use_tls = settings.SMTP_USE_TLS
        self.from_email = settings.FROM_EMAIL or settings.SMTP_USERNAME
        self.from_name = settings.FROM_NAME

    async def send_verification_email(self, to_email: str, verification_code: str) -> bool:
        """Send email verification code to user"""
        if not self._is_configured():
            logger.warning("Email service not configured. Skipping email send.")
            return False

        subject = "Email Verification - Affiliate System"
        
        # Create HTML email template
        html_content = self._create_verification_email_template(verification_code)
        
        # Create plain text version
        text_content = f"""
        Email Verification
        
        Hello,
        
        Thank you for registering with our affiliate system. Please use the following verification code to complete your registration:
        
        Verification Code: {verification_code}
        
        This code will expire in 24 hours.
        
        If you didn't request this verification, please ignore this email.
        
        Best regards,
        {self.from_name}
        """

        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email

            # Add both plain text and HTML versions
            text_part = MIMEText(text_content, "plain")
            html_part = MIMEText(html_content, "html")
            
            message.attach(text_part)
            message.attach(html_part)

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()
                
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                
                server.send_message(message)
                logger.info(f"Verification email sent to {to_email}")
                return True

        except Exception as e:
            logger.error(f"Failed to send verification email to {to_email}: {str(e)}")
            return False

    def _create_verification_email_template(self, verification_code: str) -> str:
        """Create HTML email template for verification"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Email Verification</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    border-radius: 8px 8px 0 0;
                }}
                .content {{
                    background-color: #ffffff;
                    padding: 30px;
                    border: 1px solid #e9ecef;
                }}
                .verification-code {{
                    background-color: #f8f9fa;
                    border: 2px dashed #007bff;
                    padding: 20px;
                    text-align: center;
                    font-size: 24px;
                    font-weight: bold;
                    color: #007bff;
                    margin: 20px 0;
                    border-radius: 8px;
                }}
                .footer {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    border-radius: 0 0 8px 8px;
                    font-size: 14px;
                    color: #6c757d;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 24px;
                    background-color: #007bff;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Email Verification</h1>
            </div>
            <div class="content">
                <h2>Welcome to our Affiliate System!</h2>
                <p>Thank you for registering with our affiliate system. To complete your registration, please verify your email address using the code below:</p>
                
                <div class="verification-code">
                    {verification_code}
                </div>
                
                <p><strong>Important:</strong></p>
                <ul>
                    <li>This verification code will expire in 24 hours</li>
                    <li>Enter this code in the verification form to complete your registration</li>
                    <li>If you didn't request this verification, please ignore this email</li>
                </ul>
                
                <p>If you have any questions, please contact our support team.</p>
            </div>
            <div class="footer">
                <p>This email was sent by {self.from_name}</p>
                <p>Please do not reply to this email</p>
            </div>
        </body>
        </html>
        """

    def _is_configured(self) -> bool:
        """Check if email service is properly configured"""
        return bool(
            self.smtp_username and 
            self.smtp_password and 
            self.from_email
        )

# Create global email service instance
email_service = EmailService()
