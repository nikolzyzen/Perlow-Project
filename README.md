# SMS Survey System

A modern SMS-based wellbeing survey system with beautiful React frontend and Flask backend.

## 🚀 Quick Start

### One-Command Setup & Start
```bash
python quick_start.py
```

That's it! The system will:
- ✅ Create virtual environment
- ✅ Install all dependencies  
- ✅ Start the server
- ✅ Open admin dashboard at http://localhost:5001/admin

### Manual Setup (Alternative)
```bash
# 1. Setup
python setup.py

# 2. Start
python start.py
```

### Access Your System
- **Admin Dashboard**: http://localhost:5001/admin
- **API Stats**: http://localhost:5001/api/stats
- **User Analytics**: http://localhost:5001/feedback/4/1

## 📁 Simplified File Structure

```
sms_survey_system/
├── sms_survey.py          # Main application (everything in one file)
├── requirements.txt       # Python dependencies
├── README.md             # Complete documentation
├── quick_start.py        # One-command setup & start
├── setup.py              # Manual setup script
├── start.py              # Manual start script
├── src/                  # React frontend (optional)
└── venv/                 # Virtual environment
```

## 📱 Features

### Core Functionality
- **SMS Surveys**: Send wellbeing surveys via SMS
- **Mock SMS Mode**: Test without real SMS costs
- **User Management**: Add/edit users and campaigns
- **Analytics**: Beautiful personal analytics for users
- **Admin Dashboard**: Modern Pinterest-like UI

### Modern UI
- **React Frontend**: Beautiful, responsive interface
- **Real-time Data**: Live API integration
- **Mobile Optimized**: Works on all devices
- **Smooth Animations**: Professional user experience

## Development

### Frontend Development (Optional)
```bash
# Install Node.js first, then:
cd frontend
npm install
npm run dev
```

### API Endpoints
- `GET /api/stats` - Dashboard statistics
- `GET /api/users` - All users
- `GET /api/campaigns` - All campaigns
- `GET /api/responses` - Recent responses
- `GET /api/analytics/<user_id>/<campaign_id>` - User analytics

## Troubleshooting

### Virtual Environment Issues
**Always use virtual environment:**
```bash

source venv/bin/activate
python sms_survey.py

```

### Twilio Configuration
The system uses **Mock SMS** by default. To use real Twilio:
1. Set `USE_MOCK_SMS=false` in `.env`
2. Add your Twilio credentials:
   ```
   TWILIO_ACCOUNT_SID=your_account_sid
   TWILIO_AUTH_TOKEN=your_auth_token
   TWILIO_PHONE_NUMBER=your_phone_number
   ```

### Common Issues
- **Jinja2 Error**: Use virtual environment
- **Port 5001 in use**: Change PORT in `.env`
- **Database errors**: Delete `instance/survey.db` to reset

## 📊 Usage

### Admin Dashboard
1. Go to http://localhost:5001/admin
2. Add users and campaigns
3. Send test SMS surveys
4. View responses and analytics

### User Experience
1. Users receive SMS surveys
2. They respond with ratings (e.g., "8/7/9/Spent time with family")
3. System automatically sends analytics link
4. Users view their personalized insights

### SMS Format
Users respond with: `joy/achievement/meaningfulness/influence_text`
Example: `8/7/9/Spent time with family`

## 🎯 Project Structure

```
sms_survey_system/
├── sms_survey.py          # Main application (everything in one file)
├── requirements.txt       # Python dependencies
├── .env                   # Environment configuration
├── README.md             # This file
├── frontend/             # React frontend (optional)
└── instance/             # Database files
```

## 🚀 Production

### Simple Deployment
```bash
# Build frontend (if using React)
cd frontend && npm run build:prod

# Run production server
source venv/bin/activate
python sms_survey.py
```

### Environment Variables
Set these in production:
- `FLASK_ENV=production`
- `SECRET_KEY=your_secure_secret_key`
- `DATABASE_URL=your_production_database_url`

## 📈 Analytics

The system tracks:
- **Joy**: How happy users feel
- **Achievement**: How accomplished they feel
- **Meaningfulness**: How purposeful their activities are
- **Influence**: What affected their day

Users get personalized insights and can track their wellbeing over time.

## 🎉 Success!

When everything works, you'll see:
```
🚀 Starting SMS Survey System...
✅ Virtual environment activated
🌐 Starting Flask server on http://localhost:5001
📱 Access your admin dashboard at: http://localhost:5001/admin
```

Happy surveying! 📊✨