# Affiliate Management System

A FastAPI-based affiliate management system with email verification, admin approval workflow, and unique affiliate link tracking.

## Features

- 🔐 **Secure Authentication** - JWT-based auth with rate limiting
- 📧 **Email Verification** - Required email verification for affiliate registration
- 👥 **Admin Dashboard** - Approve/reject affiliate requests
- 🔗 **Unique Affiliate Links** - Generate and track affiliate links
- 🛡️ **Security** - Password hashing, CORS protection, input validation
- 📊 **MongoDB Integration** - Scalable document-based storage

## Quick Start

### 1. Prerequisites

- Python 3.8+
- MongoDB (local or cloud)
- Email service (Gmail, Outlook, etc.)

### 2. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd affiliate_system

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the project root:

```bash
# Database Configuration
DATABASE_URL=mongodb://localhost:27017/affiliate_db

# Security Configuration
SECRET_KEY=your-super-secret-key-here-make-it-long-and-random
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Admin Configuration
ADMIN_REGISTRATION_LINK=ADMIN-SECURE-LINK-2024
ADMIN_EMAIL=admin@yourcompany.com
ADMIN_PASSWORD=your-secure-admin-password

# Application Configuration
BASE_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Email Configuration (Required for email verification)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
FROM_EMAIL=your-email@gmail.com
FROM_NAME=Your Company Name
```

### 4. Email Setup (Gmail Example)

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate App Password**:
   - Go to [Google Account Settings](https://myaccount.google.com/)
   - Security → 2-Step Verification → App passwords
   - Generate new app password for "Mail"
   - Use this password as `SMTP_PASSWORD`

### 5. Database Setup

Make sure MongoDB is running:

```bash
# Start MongoDB (if installed locally)
mongod

# Or use MongoDB Atlas (cloud)
# Update DATABASE_URL in .env file
```

### 6. Run the Application

```bash
# Start the server
python main.py

# Or using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## API Endpoints

### Authentication
- `POST /login` - User login

### Email Verification
- `POST /email/send-verification` - Send verification code
- `POST /email/verify-email` - Verify email with code
- `POST /email/resend-verification` - Resend verification code
- `GET /email/check-verification/{email}` - Check verification status

### Affiliate Registration
- `POST /register/{admin_link}` - Register as affiliate (requires email verification)
- `GET /affiliate/profile` - Get affiliate profile
- `GET /ref/{unique_link}` - Track affiliate link clicks

### Admin Operations
- `GET /admin/registration-link` - Get admin registration link
- `GET /admin/pending-requests` - Get pending affiliate requests
- `GET /admin/all-requests` - Get all requests (paginated)
- `POST /admin/review-request` - Approve/reject affiliate requests
- `GET /admin/affiliates` - Get all approved affiliates

## Usage Flow

### For Affiliates:

1. **Email Verification**:
   ```bash
   # Send verification email
   POST /email/send-verification
   {
     "email": "user@example.com"
   }
   
   # Verify email with code
   POST /email/verify-email
   {
     "email": "user@example.com",
     "verification_code": "123456"
   }
   ```

2. **Register as Affiliate**:
   ```bash
   POST /register/ADMIN-SECURE-LINK-2024
   {
     "name": "John Doe",
     "email": "user@example.com",
     "password": "securepassword",
     "location": "New York",
     "language": "English",
     "onemove_link": "https://onemove.com/ref/user",
     "puprime_link": "https://puprime.com/ref/user"
   }
   ```

3. **Login and Get Profile**:
   ```bash
   # Login
   POST /login
   {
     "username": "user@example.com",
     "password": "securepassword"
   }
   
   # Get affiliate profile (use Bearer token)
   GET /affiliate/profile
   ```

### For Admins:

1. **Login**:
   ```bash
   POST /login
   {
     "username": "admin@yourcompany.com",
     "password": "your-secure-admin-password"
   }
   ```

2. **Review Affiliate Requests**:
   ```bash
   # Get pending requests
   GET /admin/pending-requests
   
   # Approve request
   POST /admin/review-request
   {
     "request_id": "affiliate_request_id",
     "approve": true,
     "reason": "Approved after review"
   }
   ```

## Development

### Running in Development Mode

```bash
# With auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# With debug logging
uvicorn main:app --reload --log-level debug
```

### Testing Email Verification

1. **Without Email Service**: The system will log email attempts but continue working
2. **With Email Service**: Configure SMTP settings in `.env` file
3. **Test Endpoints**: Use the interactive docs at `/docs`

### Database Management

```bash
# Connect to MongoDB
mongosh

# View collections
use affiliate_db
show collections

# View data
db.users.find()
db.affiliate_requests.find()
db.email_verifications.find()
```

## Production Deployment

### Environment Variables for Production

```bash
# Production Database
DATABASE_URL=mongodb+srv://username:password@cluster.mongodb.net/affiliate_db

# Secure Secret Key
SECRET_KEY=your-production-secret-key-very-long-and-secure

# Production URLs
BASE_URL=https://yourdomain.com
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Production Email
SMTP_HOST=smtp.yourdomain.com
FROM_EMAIL=noreply@yourdomain.com
FROM_NAME=Your Company
```

### Docker Deployment (Optional)

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Troubleshooting

### Common Issues

1. **"Database connection failed"**
   - Check MongoDB is running
   - Verify DATABASE_URL in .env

2. **"Email service not configured"**
   - Set all SMTP variables in .env
   - Check email credentials

3. **"Invalid registration link"**
   - Use the correct admin link from `/admin/registration-link`
   - Check ADMIN_REGISTRATION_LINK in .env

4. **"Email must be verified"**
   - Complete email verification before registration
   - Check verification status at `/email/check-verification/{email}`

### Logs and Debugging

```bash
# Enable debug logging
export PYTHONPATH=.
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
import main
"
```

## Security Notes

- Change default SECRET_KEY and ADMIN_REGISTRATION_LINK
- Use strong passwords for admin accounts
- Configure CORS_ORIGINS for production
- Use HTTPS in production
- Regularly update dependencies

## Support

For issues and questions:
1. Check the logs for error messages
2. Verify environment configuration
3. Test individual endpoints using `/docs`
4. Check MongoDB connection and data
