# Affiliate Management System API

A comprehensive FastAPI-based system for managing affiliate registrations, approvals, and referral tracking.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- MongoDB
- Virtual environment (recommended)

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd tracking_be

# Create and activate virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run the application
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## 📚 API Documentation

### Interactive Documentation
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🔗 Base URL
```
http://localhost:8000
```

## 🔐 Authentication

Most endpoints require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

---

## 📋 API Endpoints

### 🏠 Root & Health Endpoints

#### GET /
**Purpose**: API information and documentation links
**Authentication**: None required

**Response**:
```json
{
  "message": "Affiliate Management System API",
  "documentation": "/docs",
  "registration_endpoint": "/register/{admin_link}"
}
```

#### GET /health
**Purpose**: Health check and database status
**Authentication**: None required

**Response**:
```json
{
  "status": "healthy",
  "database": "connected"
}
```

---

### 🔑 Authentication Endpoints

#### POST /login
**Purpose**: Login for both admin and affiliate users
**Authentication**: None required

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response**:
```json
{
  "access_token": "jwt_token_here",
  "token_type": "bearer"
}
```

**Features**:
- Rate limiting (429 if too many attempts)
- Checks if account is active
- Returns JWT token for subsequent requests

---

### 👨‍💼 Admin Endpoints

All admin endpoints require admin authentication.

#### GET /admin/registration-link
**Purpose**: Get the fixed admin registration link
**Authentication**: Admin token required

**Response**:
```json
{
  "registration_link": "ADMIN-SECURE-LINK-2024",
  "full_url": "http://127.0.0.1:8000/register/ADMIN-SECURE-LINK-2024"
}
```

#### GET /admin/pending-requests
**Purpose**: Get all pending affiliate requests
**Authentication**: Admin token required

**Response**: Array of `AffiliateRequestResponse` objects
```json
[
  {
    "id": "request_id",
    "name": "John Doe",
    "email": "john@example.com",
    "location": "New York",
    "language": "English",
    "onemove_link": "https://onemove.com/ref/123",
    "puprime_link": "https://puprime.com/ref/456",
    "status": "pending",
    "created_at": "2025-01-15T10:30:00Z",
    "reviewed_at": null
  }
]
```

#### GET /admin/all-requests
**Purpose**: Get all affiliate requests with optional filtering
**Authentication**: Admin token required

**Query Parameters**:
- `status` (optional): "pending", "approved", "rejected"
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20)

**Response**: Paginated array of `AffiliateRequestResponse` objects

#### POST /admin/review-request
**Purpose**: Approve or reject an affiliate request
**Authentication**: Admin token required

**Request Body**:
```json
{
  "request_id": "request_id_here",
  "approve": true,
  "reason": "Optional reason for rejection"
}
```

**Response (Approval)**:
```json
{
  "message": "Affiliate approved successfully",
  "affiliate_id": "affiliate_id",
  "unique_link": "http://127.0.0.1:8000/ref/unique_link",
  "affiliate_email": "user@example.com"
}
```

**Response (Rejection)**:
```json
{
  "request": "Affiliate request rejected",
  "reason": "Reason provided or 'No reason provided'"
}
```

#### GET /admin/affiliates
**Purpose**: Get all approved affiliates
**Authentication**: Admin token required

**Query Parameters**:
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20)

**Response**: Array of `AffiliateResponse` objects with full URLs

---

### 🤝 Affiliate Endpoints

#### POST /register/{link_code}
**Purpose**: Register as a new affiliate using admin link
**Authentication**: None required

**Path Parameter**: `link_code` - Must match the admin registration link

**Request Body**:
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "password123",
  "location": "New York",
  "language": "English",
  "onemove_link": "https://onemove.com/ref/123",
  "puprime_link": "https://puprime.com/ref/456"
}
```

**Response**: `AffiliateRequestResponse` object

**Features**: Creates pending request that needs admin approval

#### GET /affiliate/profile
**Purpose**: Get current affiliate's profile
**Authentication**: Affiliate token required

**Response**: `AffiliateResponse` object with unique referral link
```json
{
  "id": "affiliate_id",
  "name": "John Doe",
  "email": "john@example.com",
  "location": "New York",
  "language": "English",
  "unique_link": "http://localhost:8000/ref/unique_link",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Note**: Admin users cannot access this endpoint

#### POST /ref/{unique_link}
**Purpose**: Register a new member through an affiliate's unique link
**Authentication**: None required

**Path Parameter**: `unique_link` - The affiliate's unique referral code

**Request Body**:
```json
{
  "full_name": "Jane Smith",
  "email": "jane@example.com",
  "password": "securepassword123",
  "timezone": "UTC+5",
  "location": "New York",
  "headline": "Professional Trader",
  "bio": "Experienced trader with 5+ years...",
  "broker_id": "BROKER123",
  "invited_person": "John Doe",
  "find_us": "Social Media"
}
```

**Response**: `ReferralResponse` object
```json
{
  "id": "referral_id",
  "affiliate_id": "affiliate_id",
  "unique_link": "unique_link",
  "full_name": "Jane Smith",
  "email": "jane@example.com",
  "timezone": "UTC+5",
  "location": "New York",
  "headline": "Professional Trader",
  "bio": "Experienced trader with 5+ years...",
  "broker_id": "BROKER123",
  "invited_person": "John Doe",
  "find_us": "Social Media",
  "created_at": "2025-01-15T10:30:00Z"
}
```

#### GET /affiliate/referrals
**Purpose**: Get all referrals for the current affiliate (paginated)
**Authentication**: Affiliate token required

**Query Parameters**:
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20)

**Response**: Array of `ReferralResponse` objects
```json
[
  {
    "id": "referral_id",
    "affiliate_id": "affiliate_id",
    "unique_link": "unique_link",
    "full_name": "Jane Smith",
    "email": "jane@example.com",
    "timezone": "UTC+5",
    "location": "New York",
    "headline": "Professional Trader",
    "bio": "Experienced trader with 5+ years...",
    "broker_id": "BROKER123",
    "invited_person": "John Doe",
    "find_us": "Social Media",
    "created_at": "2025-01-15T10:30:00Z"
  }
]
```

#### GET /affiliate/referrals/count
**Purpose**: Get total count of referrals for the current affiliate
**Authentication**: Affiliate token required

**Response**:
```json
{
  "total_referrals": 5
}
```

---

## 🔧 Debug Endpoints

#### GET /debug/check-affiliate-match
**Purpose**: Debug endpoint to check affiliate ID matching
**Authentication**: Affiliate token required

**Response**: Detailed information about affiliate and referral matching

---

## 📊 Data Models

### User Roles
- **Admin**: Can approve/reject affiliate requests, view all data
- **Affiliate**: Can view their profile and referrals, cannot access admin functions

### Request Status
- **pending**: Awaiting admin review
- **approved**: Approved by admin, affiliate account created
- **rejected**: Rejected by admin

### Pagination
All list endpoints support pagination with:
- `page`: Page number (1-based)
- `page_size`: Items per page (1-100, default 20)

---

## 🔒 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Role-based Access Control**: Admin vs Affiliate permissions
- **Rate Limiting**: Login attempt protection
- **Password Hashing**: Secure password storage
- **Input Validation**: All inputs are validated and sanitized
- **CORS Support**: Configurable cross-origin requests

---

## 🚨 Error Responses

### Common HTTP Status Codes
- **200**: Success
- **400**: Bad Request (validation error)
- **401**: Unauthorized (invalid/missing token)
- **403**: Forbidden (insufficient permissions)
- **404**: Not Found (resource doesn't exist)
- **429**: Too Many Requests (rate limited)
- **500**: Internal Server Error

### Error Response Format
```json
{
  "detail": "Error message description"
}
```

---

## 🔄 Authentication Flow

### Admin Flow
1. Login at `POST /login` with admin credentials
2. Use returned JWT token in `Authorization: Bearer <token>` header
3. Access admin endpoints to manage affiliate requests

### Affiliate Flow
1. Register at `POST /register/{admin_link}` (requires valid admin link)
2. Wait for admin approval
3. Login at `POST /login` with affiliate credentials
4. Use returned JWT token to access affiliate profile and referrals

### Public Flow
1. Anyone can register through affiliate links at `POST /ref/{unique_link}`
2. This creates referral records linked to the affiliate

---

## 🛠️ Development

### Environment Variables
Create a `.env` file with:
```env
DATABASE_URL=mongodb://localhost:27017
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=adminpassword
ADMIN_REGISTRATION_LINK=ADMIN-SECURE-LINK-2024
BASE_URL=http://localhost:8000
CORS_ORIGINS=*
```

### Database Models
- **User**: Authentication and role management
- **AffiliateRequest**: Pending affiliate applications
- **Affiliate**: Approved affiliate profiles
- **Referral**: Members registered through affiliate links
- **SystemConfig**: System configuration

---

## 📝 License

This project is licensed under the MIT License.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

---

## 📞 Support

For support and questions, please contact the development team or create an issue in the repository.
