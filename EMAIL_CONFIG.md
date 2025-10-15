# Email Configuration Guide

## Required Environment Variables

To enable email verification functionality, you need to configure the following environment variables:

### SMTP Configuration

```bash
# Email Service Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=circle1move@gmail.com
SMTP_PASSWORD=nsgkmxodgpussnma
SMTP_USE_TLS=true
FROM_EMAIL=circle1move@gmail.com
FROM_NAME=1move Community
```

### Gmail Setup (Recommended)

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate an App Password**:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate a new app password for "Mail"
   - Use this password as `SMTP_PASSWORD`

### Other Email Providers

#### Outlook/Hotmail
```bash
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USE_TLS=true
```

#### Yahoo
```bash
SMTP_HOST=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USE_TLS=true
```

#### Custom SMTP Server
```bash
SMTP_HOST=your-smtp-server.com
SMTP_PORT=587
SMTP_USE_TLS=true
```

## Email Verification Flow

1. **Send Verification**: `POST /email/send-verification`
   - Sends 6-digit verification code to email
   - Code expires in 24 hours
   - Max 3 attempts per code

2. **Verify Email**: `POST /email/verify-email`
   - Verify the 6-digit code
   - Email becomes verified for registration

3. **Resend Verification**: `POST /email/resend-verification`
   - Resend verification code if needed

4. **Check Status**: `GET /email/check-verification/{email}`
   - Check if email is verified

## Registration Process

1. User calls `/email/send-verification` with their email
2. User receives verification email with 6-digit code
3. User calls `/email/verify-email` with email and code
4. User can now register using `/register/{admin_link}`

## Email Templates

The system sends professional HTML emails with:
- Company branding
- Clear verification code display
- Expiration information
- Security instructions

## Security Features

- **Rate Limiting**: Max 3 verification attempts per code
- **Expiration**: Codes expire in 24 hours
- **Unique Codes**: 6-digit random codes
- **Email Validation**: Prevents duplicate registrations
- **Secure Storage**: Verification records stored in database

## Testing Without Email

If you don't want to configure email during development, the system will:
- Log email sending attempts
- Continue to work without actual email delivery
- Allow testing of the verification flow

## Troubleshooting

### Common Issues

1. **"Email service not configured"**
   - Check that all SMTP variables are set
   - Verify SMTP credentials are correct

2. **"Failed to send verification email"**
   - Check SMTP server settings
   - Verify app password (for Gmail)
   - Check firewall/network restrictions

3. **"Invalid verification code"**
   - Code may have expired (24 hours)
   - Max attempts exceeded (3 attempts)
   - Check code format (6 digits)

### Debug Mode

Set logging level to DEBUG to see detailed email sending logs:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```
