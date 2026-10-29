# E-Signature Feature Documentation

## Overview

The Coneshare e-signature feature (Phase 1) allows internal users to request and collect legally binding electronic signatures on PDF documents. This implementation is designed for staff, doctors, and directors within the organization.

## Key Features

- **Internal Users Only**: All signers must be logged-in Coneshare users with accounts in the organization
- **Flexible Signing Order**: Sequential (one after another) or parallel (all at once)
- **Multi-language Support**: Full English and Arabic support with RTL layout
- **OTP Verification**: One-time password sent to signer's email before signing
- **Multiple Field Types**: Signature, initials, date signed, full name, and text fields
- **Complete Audit Trail**: IP address, user agent, timestamps (Asia/Riyadh), OTP verification time, event log
- **Certificate of Completion**: Automatically generated with document hashes (SHA-256) and full audit trail
- **Admin Toggle**: Feature can be enabled/disabled system-wide via admin settings

## Setup Instructions

### 1. Enable the Feature

The e-signature feature is controlled by the `ESIGN_ENABLED` setting in the admin panel.

**To enable:**
1. Log in as an administrator
2. Navigate to Admin → Settings
3. Find `ESIGN_ENABLED` setting
4. Set to `true`
5. Save changes

When disabled, all e-signature UI is hidden and all API endpoints return 403/404.

### 2. Run Database Migrations

```bash
cd backend
python manage.py makemigrations esign
python manage.py migrate
```

### 3. Configure Email Settings

Ensure your Django email settings are properly configured. The feature sends emails for:
- Signature request notifications
- OTP verification codes
- Reminders
- Completion notifications
- Cancellation and decline notifications
- Expiration notifications

### 4. Background Tasks

The feature uses Celery for background tasks. Ensure your Celery worker is running:

```bash
celery -A backend worker -l info
```

For periodic tasks (checking expired requests):

```bash
celery -A backend beat -l info
```

## User Workflows

### Creating a Signature Request

1. Navigate to a PDF document in Coneshare
2. Click "Send for Signature" button
3. Add signers (select from organization users)
4. Choose signing order:
   - **Parallel**: All signers receive email simultaneously
   - **Sequential**: Next signer receives email only after previous signs
5. Place signature fields on the PDF:
   - Signature (draw or type)
   - Initials
   - Date Signed (auto-filled)
   - Full Name (auto-filled)
   - Text (custom input)
6. Assign each field to a signer
7. Set expiration date (optional)
8. Review and send

### Signing a Document

1. Signer receives email with link
2. Click link → redirected to Coneshare (must be logged in)
3. System verifies user is the intended signer
4. Request OTP code
5. Enter 6-digit code from email
6. Review document and fields
7. Fill each field:
   - Draw signature with mouse/touch
   - Type name (renders in handwriting-style font)
   - Fill text fields
8. Submit signature
9. Receive confirmation email when all signers complete

### Managing Requests

**View Requests:**
- Navigate to "Signatures" in sidebar
- Two tabs:
  - "Sent by Me": Requests you created
  - "Awaiting My Signature": Requests where you're a signer

**Available Actions:**
- **Send Reminder**: Notify pending signers
- **Cancel Request**: Void an in-progress request (notifies signers)
- **View Document**: Access completed signed PDF
- **Download Certificate**: Get certificate of completion

## Security & Legal Compliance

### Authentication & Authorization

- **No Anonymous Signing**: All signers must have Coneshare accounts and be logged in
- **Identity Verification**: User must authenticate with their Coneshare credentials
- **Signer Validation**: Backend verifies `request.user` matches the intended signer
- **OTP Gate**: Mandatory one-time password verification before signing
- **Token Security**: Signing tokens are unique, random, and one-time use

### Audit Trail

Every signature request includes:

1. **Signer Information**:
   - Full name and email
   - User ID in system
   - Signing order position

2. **Verification Events** (with timestamps in Asia/Riyadh timezone):
   - Email sent
   - Link opened
   - OTP requested
   - OTP verified (with verification time)
   - Each field filled
   - Signature submitted
   - Document completed

3. **Technical Metadata**:
   - IP address at signing time
   - User agent (browser/device)
   - Original document SHA-256 hash
   - Final signed document SHA-256 hash

4. **Event Log**:
   - Complete chronological record of all actions
   - Included in certificate of completion

### Certificate of Completion

Automatically generated and attached to signed PDF:

- Document title and ID
- All signer information
- Full event log with timestamps (Asia/Riyadh)
- Original and final document SHA-256 hashes
- OTP verification times
- IP addresses and user agents
- Generation timestamp

## API Reference

### Authentication

All endpoints require JWT authentication:

```
Authorization: Bearer <access_token>
```

### Endpoints

#### List Requests

```
GET /api/v1/esign/requests/?view={created|awaiting}
```

Returns signature requests. `view=created` shows requests you created, `view=awaiting` shows requests where you're a signer.

#### Create Request

```
POST /api/v1/esign/requests/
{
  "document_id": 123,
  "title": "Employment Contract",
  "message": "Please review and sign",
  "signers": [
    {"user_id": 456, "signing_order": 1},
    {"user_id": 789, "signing_order": 2}
  ],
  "signing_order": true,  // true = sequential, false = parallel
  "expires_at": "2026-12-31T23:59:59Z"
}
```

#### Update Fields

```
PATCH /api/v1/esign/requests/{id}/update_fields/
{
  "fields": [
    {
      "signer_id": 1,
      "field_type": "signature",
      "page_number": 1,
      "x": 10.0,  // percentage
      "y": 80.0,  // percentage
      "width": 30.0,
      "height": 8.0,
      "required": true
    }
  ]
}
```

#### Send Request

```
POST /api/v1/esign/requests/{id}/send/
```

Sends email to signers and activates the request.

#### Get Signing Data

```
GET /api/v1/esign/sign/{token}/
```

Retrieves signing page data. User must be authenticated and must be the assigned signer.

#### Request OTP

```
POST /api/v1/esign/sign/{token}/request_otp/
```

Sends 6-digit OTP to signer's email. Valid for 10 minutes, max 5 attempts.

#### Verify OTP

```
POST /api/v1/esign/sign/{token}/verify_otp/
{
  "code": "123456"
}
```

#### Submit Signature

```
POST /api/v1/esign/sign/{token}/submit/
{
  "fields": [
    {
      "field_id": 1,
      "value": "data:image/png;base64,..."  // for drawn signatures
    },
    {
      "field_id": 2,
      "value": "John Doe"  // for typed/text fields
    }
  ]
}
```

#### Decline to Sign

```
POST /api/v1/esign/sign/{token}/decline/
{
  "reason": "I need more time to review"
}
```

#### Cancel Request

```
POST /api/v1/esign/requests/{id}/cancel/
```

Only requester or admin can cancel. Notifies all pending signers.

#### Send Reminder

```
POST /api/v1/esign/requests/{id}/remind/
```

Sends reminder email to all pending signers.

## Troubleshooting

### Emails Not Sending

1. Check Django email settings in `backend/backend/settings.py`
2. Verify Celery worker is running
3. Check Celery logs for errors
4. Test email configuration:
   ```python
   from django.core.mail import send_mail
   send_mail('Test', 'Test message', 'from@example.com', ['to@example.com'])
   ```

### OTP Not Received

1. Check spam/junk folder
2. Verify user's email is correct
3. Check Celery task queue
4. Look for email errors in logs

### PDF Not Rendering

1. Verify fonts are in `backend/esign/fonts/`:
   - `Amiri-Regular.ttf` (Arabic support)
   - `DancingScript-Regular.ttf` (handwriting style)
2. Check ReportLab and pypdf are installed
3. Review PDF generation logs

### Feature Not Visible

1. Verify `ESIGN_ENABLED` is `true` in admin settings
2. Refresh user's browser
3. Check sidebar visibility filter in `SidebarContent.jsx`
4. Verify user has necessary permissions

### Sequential Signing Issues

1. Previous signer must complete before next can sign
2. Check signer status and signing_order values
3. Verify email was sent to next signer
4. Check Celery task logs for email sending

## Fonts & Localization

### Supported Languages

- **English**: Full support
- **Arabic**: Full support with RTL layout

### Fonts

**Backend (PDF generation):**
- **Amiri**: Arabic text support
- **Dancing Script**: Handwriting-style for typed signatures

**Frontend:**
- Localization files: `frontend/src/locales/en/` and `frontend/src/locales/ar/`
- RTL layout automatically applied for Arabic

## Testing

### Run Backend Tests

```bash
cd backend
pytest esign/tests/ -v
```

Tests cover:
- Feature toggle (ON/OFF)
- Authentication requirements
- OTP verification gate
- Sequential vs parallel workflows
- Permission checks (only assigned signer can sign)
- Audit trail recording
- Request cancellation
- Decline workflow

### Manual Testing Checklist

- [ ] Enable feature in admin
- [ ] Create signature request with multiple signers
- [ ] Receive email with signing link
- [ ] Login required to access signing page
- [ ] OTP verification required
- [ ] Draw signature works
- [ ] Type signature works
- [ ] All fields can be filled
- [ ] Submit creates signed PDF
- [ ] Certificate attached to PDF
- [ ] All signers receive completion email
- [ ] Sequential order enforced
- [ ] Reminder emails work
- [ ] Cancel request notifies signers
- [ ] Decline records reason
- [ ] Expired requests marked automatically

## Limitations & Future Enhancements

### Current Limitations (Phase 1)

- Internal users only (no public/anonymous signing)
- PDF documents only
- Single document per request
- No image upload for signatures
- No API for external integrations
- No bulk operations

### Planned for Future Phases

- Public signing (email-only signers)
- Multiple documents per request
- Image upload for signatures
- Advanced field types (checkboxes, radio buttons)
- Templates and reusable workflows
- API webhooks for completion events
- Mobile app support
- Advanced analytics and reporting

## Support

For issues or questions:
- Email: dev@coneshare.com
- Check logs: `backend/logs/` and Celery output
- Review audit trail in certificate for debugging

## License

This feature is part of Coneshare (Allure Clinic fork). All rights reserved.
