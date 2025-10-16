# Frontend Integration Guide

## How to Handle Affiliate Redirects

When users click on affiliate links like `https://api.domainkini.com/ref/hxVaNZO003WQm7wTpn40`, they will be redirected to your frontend with affiliate information.

### Backend Behavior

The backend now has a new endpoint:
- **GET** `/ref/{unique_link}` - Redirects to frontend with affiliate info

### Redirect URL Format

Users will be redirected to:
```
https://1move-final.vercel.app/register?invited_by=John%20Doe&affiliate_email=john@example.com&affiliate_link=hxVaNZO003WQm7wTpn40
```

### Query Parameters

- `invited_by` - The affiliate's name (URL encoded)
- `affiliate_email` - The affiliate's email (URL encoded)  
- `affiliate_link` - The unique affiliate link code

### Frontend Implementation

#### 1. Extract Query Parameters

```javascript
// In your registration page component
import { useSearchParams } from 'react-router-dom'; // or useRouter for Next.js

function RegistrationPage() {
  const [searchParams] = useSearchParams();
  
  // Extract affiliate info from URL
  const invitedBy = searchParams.get('invited_by');
  const affiliateEmail = searchParams.get('affiliate_email');
  const affiliateLink = searchParams.get('affiliate_link');
  
  // Pre-fill the "invited by" field
  const [invitedByField, setInvitedByField] = useState(invitedBy || '');
  
  return (
    <form>
      {/* Other form fields */}
      
      <div className="form-group">
        <label htmlFor="invitedBy">Invited By / Referred By</label>
        <input
          type="text"
          id="invitedBy"
          value={invitedByField}
          onChange={(e) => setInvitedByField(e.target.value)}
          placeholder="Who referred you?"
          readOnly={!!invitedBy} // Make read-only if pre-filled
        />
      </div>
      
      {/* Hidden field to store affiliate link for submission */}
      {affiliateLink && (
        <input type="hidden" name="affiliate_link" value={affiliateLink} />
      )}
    </form>
  );
}
```

#### 2. Next.js Implementation

```javascript
// pages/register.js or app/register/page.js
import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';

export default function RegisterPage() {
  const router = useRouter();
  const [invitedBy, setInvitedBy] = useState('');
  const [affiliateLink, setAffiliateLink] = useState('');
  
  useEffect(() => {
    // Extract query parameters
    const { invited_by, affiliate_link } = router.query;
    
    if (invited_by) {
      setInvitedBy(decodeURIComponent(invited_by));
    }
    
    if (affiliate_link) {
      setAffiliateLink(affiliate_link);
    }
  }, [router.query]);
  
  return (
    <div>
      <h1>Registration</h1>
      <form>
        {/* Other form fields */}
        
        <div>
          <label>Invited By:</label>
          <input
            type="text"
            value={invitedBy}
            onChange={(e) => setInvitedBy(e.target.value)}
            placeholder="Who referred you?"
            readOnly={!!router.query.invited_by}
          />
        </div>
        
        {/* Hidden field for affiliate link */}
        {affiliateLink && (
          <input type="hidden" name="affiliate_link" value={affiliateLink} />
        )}
      </form>
    </div>
  );
}
```

#### 3. Form Submission

When submitting the registration form, include the affiliate link:

```javascript
const handleSubmit = async (formData) => {
  const registrationData = {
    ...formData,
    affiliate_link: affiliateLink, // Include the affiliate link
  };
  
  // Submit to your backend API
  const response = await fetch('/api/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(registrationData),
  });
};
```

### Backend API Endpoint

Make sure your frontend submits to the correct endpoint:

```javascript
// Submit to the new endpoint
const response = await fetch(`/ref/${affiliateLink}/register`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(registrationData),
});
```

### Error Handling

Handle cases where affiliate link is invalid:

```javascript
const handleSubmit = async (formData) => {
  try {
    const response = await fetch(`/ref/${affiliateLink}/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(formData),
    });
    
    if (!response.ok) {
      if (response.status === 404) {
        alert('Invalid affiliate link. Please contact support.');
        return;
      }
      throw new Error('Registration failed');
    }
    
    const result = await response.json();
    console.log('Registration successful:', result);
    
  } catch (error) {
    console.error('Registration error:', error);
    alert('Registration failed. Please try again.');
  }
};
```

### Configuration

Update your `.env` file to set the frontend URL:

```env
FRONTEND_URL=https://1move-final.vercel.app
```

### Testing

1. Create an affiliate account
2. Get their unique link from `/admin/affiliates`
3. Visit `https://api.domainkini.com/ref/{unique_link}`
4. Verify you're redirected to frontend with affiliate info
5. Check that the "invited by" field is pre-filled

### Example Flow

1. **Affiliate shares link**: `https://api.domainkini.com/ref/hxVaNZO003WQm7wTpn40`
2. **User clicks link**: Redirected to `https://1move-final.vercel.app/register?invited_by=John%20Doe&affiliate_email=john@example.com&affiliate_link=hxVaNZO003WQm7wTpn40`
3. **Frontend shows**: "Invited By" field pre-filled with "John Doe"
4. **User registers**: Form includes affiliate link for tracking
5. **Backend processes**: Creates referral record linked to affiliate
