# WhatsApp Excel Export System

## Overview
Automated system that exports WhatsApp messages to Excel files and emails them to designated recipients every 15 minutes.

## Features
- **Automated Export**: Runs every 15 minutes via APScheduler
- **Workspace Separation**: Separate exports for each workspace
- **Email Distribution**: Automatic email delivery with Excel attachments
- **File Management**: Automatic cleanup of old files (7 days)
- **Error Handling**: Comprehensive logging and error recovery
- **Manual Triggers**: Admin can trigger exports manually

## Configuration

### Environment Variables
```bash
# SMTP Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Export Configuration
EXPORT_INTERVAL_MINUTES=15
EXPORT_CLEANUP_DAYS=7

# Workspace Email Configuration
WORKSPACE_{WORKSPACE_ID}_EMAIL=recipient@domain.com
```

### Workspace Email Setup
For each workspace, add an environment variable:
```bash
WORKSPACE_507f1f77bcf86cd799439011_EMAIL=sales@company1.com
WORKSPACE_507f1f77bcf86cd799439012_EMAIL=team@company2.com
```

## Excel File Format

### Columns (in exact order):
1. **Sender Phone Number** - Phone number that sent the message
2. **Receiver Phone Number** - Phone number that received the message  
3. **Message Content** - The actual message text
4. **Timestamp** - Format: YYYY-MM-DD HH:MM:SS
5. **Status** - One of: "sent_via_ai", "sent_by_human", "received"
6. **Workspace ID** - MongoDB ObjectId of the workspace

### File Organization:
```
exports/
├── acme_corp/
│   ├── acme_corp_whatsapp_messages_2025-01-15_14-30.xlsx
│   └── acme_corp_whatsapp_messages_2025-01-15_14-45.xlsx
└── tech_startup/
    ├── tech_startup_whatsapp_messages_2025-01-15_14-30.xlsx
    └── tech_startup_whatsapp_messages_2025-01-15_14-45.xlsx
```

## API Endpoints

### Manual Export
```http
POST /exports/manual/{workspace_id}?email=recipient@domain.com&hours=24
```

### Export Statistics
```http
GET /exports/statistics/{workspace_id}?days=7
```

### Scheduler Status
```http
GET /exports/scheduler/status
```

### Test Email Configuration
```http
POST /exports/test-email?workspace_id={id}&test_email=test@domain.com
```

### Export Logs
```http
GET /exports/logs/{workspace_id}?limit=20
```

### Trigger System-wide Export (Admin Only)
```http
POST /exports/trigger-now
```

## Database Collections

### export_logs
```javascript
{
  _id: ObjectId,
  workspace_id: String,
  export_type: "whatsapp_messages",
  export_timestamp: Date,
  message_count: Number,
  file_path: String,
  email_sent_to: String,
  status: "completed" | "failed",
  error_message: String,
  created_at: Date,
  updated_at: Date
}
```

### system_logs
```javascript
{
  _id: ObjectId,
  event_type: "success" | "error" | "cleanup" | "health_check",
  message: String,
  timestamp: Date,
  service: "excel_export_scheduler"
}
```

## Monitoring

### Health Checks
The system includes comprehensive health monitoring:
- Export scheduler status
- SMTP configuration validation
- File system write permissions
- Workspace email configuration checks

### Logging
All export activities are logged with:
- Export success/failure
- Message counts
- Email delivery status
- File cleanup operations
- Error details

## Error Handling

### Common Issues and Solutions:

1. **No Email Configured**
   - Add `WORKSPACE_{ID}_EMAIL` environment variable
   - Restart the application

2. **SMTP Authentication Failed**
   - Verify SMTP credentials
   - Check if 2FA requires app password

3. **File Permission Errors**
   - Ensure write permissions on exports directory
   - Check disk space availability

4. **No Messages to Export**
   - Normal behavior - no email sent
   - Check message activity in workspace

## Manual Testing

### Test Email Configuration:
```bash
curl -X POST "http://localhost:8000/exports/test-email?workspace_id=YOUR_WORKSPACE_ID&test_email=test@domain.com" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Trigger Manual Export:
```bash
curl -X POST "http://localhost:8000/exports/manual/YOUR_WORKSPACE_ID?email=recipient@domain.com&hours=24" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Production Deployment

1. **Environment Setup**:
   - Configure all required environment variables
   - Set up SMTP server credentials
   - Configure workspace email addresses

2. **Monitoring**:
   - Monitor `/exports/scheduler/status` endpoint
   - Check system logs for export failures
   - Verify email delivery

3. **Maintenance**:
   - Files are automatically cleaned up after 7 days
   - Monitor disk space in exports directory
   - Review export statistics regularly

## Security Considerations

- Email credentials stored securely in environment variables
- File access restricted to application user
- Automatic file cleanup prevents disk space issues
- Workspace isolation ensures data privacy