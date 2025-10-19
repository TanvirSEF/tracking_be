# Email Verification System Setup Guide

## 🎯 Overview

Your affiliate management system now includes a comprehensive email verification system that ensures all user registrations are validated through email confirmation.

## 🔧 Configuration

### Environment Variables

Add these variables to your `.env` file:

```env
# Email Verification Settings
EMAIL_VERIFICATION_ENABLED=true
EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS=24

# SMTP Configuration (Gmail example)
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USERNAME=your-email@gmail.com
EMAIL_SMTP_PASSWORD=your-app-password
EMAIL_FROM_NAME=Affiliate Management System
EMAIL_FROM_EMAIL=your-email@gmail.com
```

### Gmail Setup (Recommended)

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate App Password**:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate password for "Mail"
   - Use this password in `EMAIL_SMTP_PASSWORD`

### Other Email Providers

#### Outlook/Hotmail
```env
EMAIL_SMTP_HOST=smtp-mail.outlook.com
EMAIL_SMTP_PORT=587
```

#### Yahoo
```env
EMAIL_SMTP_HOST=smtp.mail.yahoo.com
EMAIL_SMTP_PORT=587
```

#### Custom SMTP
```env
EMAIL_SMTP_HOST=your-smtp-server.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USERNAME=your-username
EMAIL_SMTP_PASSWORD=your-password
```

## 🚀 Features

### ✅ What's Included

1. **Email Verification for All User Types**:
   - Admin registration
   - Affiliate registration
   - Referral registration

2. **Professional Email Templates**:
   - HTML and plain text versions
   - Responsive design
   - Branded styling
   - Security warnings

3. **Token Management**:
   - Secure token generation
   - 24-hour expiration
   - One-time use tokens
   - Automatic cleanup

4. **User Experience**:
   - Welcome emails after verification
   - Resend verification functionality
   - Clear error messages
   - Status tracking

### 🔒 Security Features

- **Token Expiration**: 24-hour default (configurable)
- **One-time Use**: Tokens become invalid after use
- **Rate Limiting**: Prevents spam
- **Secure Generation**: Cryptographically secure tokens
- **Email Validation**: Real email addresses required

## 📧 Email Flow

### 1. Registration Process
```
User Registers → Email Sent → User Clicks Link → Account Activated → Welcome Email
```

### 2. Email Types
- **Verification Email**: Sent immediately after registration
- **Welcome Email**: Sent after successful verification
- **Resend Email**: Available if user doesn't receive verification

## 🛠️ API Endpoints

### New Endpoints Added

#### Verify Email
```http
POST /verify-email/{token}
```
**Response:**
```json
{
  "message": "Email verified successfully",
  "type": "admin|affiliate|referral",
  "email": "user@example.com"
}
```

#### Resend Verification
```http
POST /resend-verification
```
**Request:**
```json
{
  "email": "user@example.com",
  "user_type": "admin|affiliate|referral"
}
```

**Response:**
```json
{
  "message": "Verification email sent successfully",
  "email": "user@example.com"
}
```

## 🔄 Updated Registration Flow

### Admin Registration
1. Admin registers with secure link
2. **NEW**: Verification email sent
3. **NEW**: Admin must verify email
4. Account activated after verification
5. **NEW**: Welcome email sent

### Affiliate Registration
1. Affiliate submits application
2. **NEW**: Verification email sent
3. **NEW**: Affiliate must verify email
4. Admin can only approve verified requests
5. **NEW**: Welcome email sent after approval

### Referral Registration
1. User registers through affiliate link
2. **NEW**: Verification email sent
3. **NEW**: User must verify email
4. **NEW**: Welcome email sent after verification

## 📊 Database Changes

### New Model: `EmailVerificationToken`
```python
class EmailVerificationToken(Document):
    email: str
    token: str
    token_type: str  # "admin_registration", "affiliate_registration", "referral_registration"
    expires_at: datetime
    is_used: bool
    created_at: datetime
    used_at: Optional[datetime]
```

### Updated Models
- **User**: Added `is_email_verified: bool`
- **AffiliateRequest**: Added `is_email_verified: bool`

## 🎨 Email Templates

### Professional Design Features
- **Responsive Layout**: Works on all devices
- **Branded Styling**: Professional appearance
- **Security Warnings**: Clear expiration notices
- **Call-to-Action Buttons**: Easy verification
- **Fallback Links**: Manual link copying option

### Template Types
1. **Verification Email**: Account activation
2. **Welcome Email**: Post-verification confirmation

## ⚙️ Configuration Options

### Enable/Disable Verification
```env
EMAIL_VERIFICATION_ENABLED=false  # Disable for development
```

### Token Expiration
```env
EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS=48  # Custom expiration
```

### Email Settings
```env
EMAIL_FROM_NAME=Your Company Name
EMAIL_FROM_EMAIL=noreply@yourcompany.com
```

## 🚨 Error Handling

### Common Scenarios
- **Invalid Token**: Clear error message
- **Expired Token**: Automatic resend option
- **Already Verified**: Prevent duplicate verification
- **Email Not Found**: Proper error handling

### User-Friendly Messages
- Clear instructions
- Helpful error descriptions
- Resend functionality
- Status indicators

## 🔧 Development Setup

### 1. Install Dependencies
All required packages are already in `requirements.txt`

### 2. Configure Environment
```bash
# Copy and edit environment file
cp .env.example .env
# Add your email settings
```

### 3. Test Email Sending
```python
# Test in Python shell
from email_service import email_service
await email_service.send_verification_email("test@example.com", "test-token", "admin")
```

## 🚀 Production Deployment

### 1. Environment Variables
Set all email configuration in production environment

### 2. SMTP Service
Consider using dedicated email services:
- **SendGrid**: Professional email delivery
- **Mailgun**: Developer-friendly
- **Amazon SES**: Cost-effective
- **Postmark**: Reliable delivery

### 3. Monitoring
- Monitor email delivery rates
- Track verification completion
- Set up alerts for failures

## 📈 Benefits

### Security
- **Prevents Fake Accounts**: Only real email addresses
- **Reduces Spam**: Verified users only
- **Account Security**: Email ownership verification

### User Experience
- **Professional Communication**: Branded emails
- **Clear Instructions**: Easy verification process
- **Resend Options**: User-friendly recovery

### Business Value
- **Quality Leads**: Verified users only
- **Reduced Support**: Fewer fake account issues
- **Better Analytics**: Real user data

## 🔍 Troubleshooting

### Common Issues

#### Emails Not Sending
1. Check SMTP credentials
2. Verify firewall settings
3. Test with different email provider

#### Tokens Not Working
1. Check token expiration
2. Verify database connection
3. Check for token reuse

#### Template Issues
1. Verify HTML syntax
2. Test in different email clients
3. Check encoding settings

### Debug Mode
```env
EMAIL_VERIFICATION_ENABLED=false  # Disable for testing
```

## 📞 Support

If you encounter issues:
1. Check environment variables
2. Test SMTP connection
3. Verify database connectivity
4. Review error logs

The email verification system is now fully integrated and ready for production use!
