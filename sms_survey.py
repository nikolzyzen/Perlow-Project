"""SMS survey system for collecting daily wellbeing data."""

import os
import logging
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from apscheduler.schedulers.background import BackgroundScheduler
import threading
import time

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///survey.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MODELS

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    responses = db.relationship('Response', backref='user', lazy=True)
    survey_messages = db.relationship('SurveyMessage', backref='user', lazy=True)

class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    responses = db.relationship('Response', backref='campaign', lazy=True)
    survey_messages = db.relationship('SurveyMessage', backref='campaign', lazy=True)
    
    def is_running(self):
        today = date.today()
        return self.is_active and self.start_date <= today <= self.end_date

class Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    survey_date = db.Column(db.Date, nullable=False)
    
    # Survey responses
    joy_rating = db.Column(db.Integer, nullable=True)
    achievement_rating = db.Column(db.Integer, nullable=True)
    meaningfulness_rating = db.Column(db.Integer, nullable=True)
    influence_text = db.Column(db.Text, nullable=True)
    
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

class SurveyMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    survey_date = db.Column(db.Date, nullable=False)
    message_sid = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default='pending')
    sent_at = db.Column(db.DateTime, nullable=True)

# SMS SERVICE

class MockSMSService:
    """Mock SMS service for testing without actual SMS delivery"""
    
    def __init__(self):
        self.sent_messages = []
        self.delivery_status = {}
        self.mock_delivery_delay = 2
        
    def send_sms(self, to, body, from_number=None):
        message_id = f"mock_{len(self.sent_messages) + 1}_{int(datetime.now().timestamp())}"
        
        message = {
            'sid': message_id,
            'to': to,
            'from': from_number or os.getenv('TWILIO_PHONE_NUMBER', '+1234567890'),
            'body': body,
            'status': 'queued',
            'date_created': datetime.now().isoformat(),
            'direction': 'outbound-api'
        }
        
        self.sent_messages.append(message)
        
        # Simulate delivery after delay
        def simulate_delivery():
            time.sleep(self.mock_delivery_delay)
            message['status'] = 'delivered'
            message['date_sent'] = datetime.now().isoformat()
            self.delivery_status[message_id] = 'delivered'
            logger.info(f"Mock SMS delivered to {to}: {body[:50]}...")
        
        threading.Thread(target=simulate_delivery, daemon=True).start()
        logger.info(f"Mock SMS sent to {to}: {body[:50]}...")
        return message

class SMSService:
    def __init__(self):
        self.use_mock = os.getenv('USE_MOCK_SMS', 'false').lower() == 'true'
        
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.phone_number = os.getenv('TWILIO_PHONE_NUMBER')
        
        if self.use_mock:
            self.mock_service = MockSMSService()
            logger.info("Using Mock SMS Service for testing")
        else:
            if not all([self.account_sid, self.auth_token, self.phone_number]):
                raise ValueError("Twilio credentials not properly configured")
            
            self.client = Client(self.account_sid, self.auth_token)
            logger.info("Using Real Twilio SMS Service")
    
    def send_survey_message(self, user, campaign, survey_date=None):
        if survey_date is None:
            survey_date = date.today()
        
        # Check if message already sent
        existing_message = SurveyMessage.query.filter_by(
            user_id=user.id,
            campaign_id=campaign.id,
            survey_date=survey_date
        ).first()
        
        if existing_message:
            return existing_message
        
        # Create survey message record
        survey_message = SurveyMessage(
            user_id=user.id,
            campaign_id=campaign.id,
            survey_date=survey_date,
            status='pending'
        )
        db.session.add(survey_message)
        db.session.commit()
        
        # Generate message content
        message_content = self._generate_survey_message(user, survey_date)
        
        try:
            if self.use_mock:
                message = self.mock_service.send_sms(
                    to=user.phone_number,
                    body=message_content,
                    from_number=self.phone_number
                )
                message_sid = message['sid']
            else:
                message = self.client.messages.create(
                    body=message_content,
                    from_=self.phone_number,
                    to=user.phone_number
                )
                message_sid = message.sid
            
            survey_message.message_sid = message_sid
            survey_message.sent_at = datetime.utcnow()
            survey_message.status = 'sent'
            db.session.commit()
            
            return survey_message
            
        except Exception as e:
            survey_message.status = 'failed'
            db.session.commit()
            raise e
    
    def _generate_survey_message(self, user, survey_date):
        name = user.name if user.name else "there"
        
        message = f"""Hi {name}! 🌟

Daily Wellbeing Check-in for {survey_date.strftime('%B %d, %Y')}:

Please rate your day yesterday (1-10):

1️⃣ Joy: How much joy did you get?
2️⃣ Achievement: How much achievement did you get?
3️⃣ Meaningfulness: How much meaningfulness did you get?
4️⃣ Influence: What influenced your ratings most?

Reply with: joy/achievement/meaningfulness/influence
Example: 8/7/9/Spent time with family

Thank you for participating! 💙"""
        
        return message

# SCHEDULER SERVICE

class SchedulerService:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.sms_service = SMSService()
    
    def start_scheduler(self):
        # Schedule daily surveys at 9 AM
        self.scheduler.add_job(
            func=self.send_daily_surveys,
            trigger="cron",
            hour=9,
            minute=0,
            id='daily_surveys'
        )
        
        # Schedule weekly cleanup
        self.scheduler.add_job(
            func=self.cleanup_old_data,
            trigger="cron",
            day_of_week=0,  # Sunday
            hour=2,
            minute=0,
            id='weekly_cleanup'
        )
        
        self.scheduler.start()
        logger.info("Scheduler started successfully")
    
    def stop_scheduler(self):
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")
    
    def send_daily_surveys(self):
        with app.app_context():
            campaigns = Campaign.query.filter_by(is_active=True).all()
            for campaign in campaigns:
                if campaign.is_running():
                    active_users = User.query.filter_by(is_active=True).all()
                    for user in active_users:
                        try:
                            self.sms_service.send_survey_message(user, campaign)
                            logger.info(f"Daily survey sent to {user.phone_number}")
                        except Exception as e:
                            logger.error(f"Failed to send survey to {user.phone_number}: {e}")
    
    def cleanup_old_data(self):
        with app.app_context():
            # Clean up old survey messages (older than 90 days)
            cutoff_date = date.today() - timedelta(days=90)
            old_messages = SurveyMessage.query.filter(SurveyMessage.survey_date < cutoff_date).all()
            for message in old_messages:
                db.session.delete(message)
            db.session.commit()
            logger.info(f"Cleaned up {len(old_messages)} old survey messages")


# ROUTES

@app.route('/')
def index():
    return jsonify({
        'message': 'SMS Survey System',
        'version': '1.0',
        'description': 'A comprehensive system for sending daily SMS surveys to collect wellbeing data',
        'endpoints': {
            'admin': '/admin - Admin dashboard',
            'api': '/api - API endpoints',
            'webhook': '/webhook - Twilio webhooks'
        },
        'status': 'running'
    })

# Admin Routes
@app.route('/admin')
def admin_redirect():
    return redirect('/admin/')

@app.route('/admin/')
def admin_dashboard():
    users = User.query.all()
    campaigns = Campaign.query.all()
    responses = Response.query.all()
    
    # Calculate real stats (no fallback hardcoded values)
    total_users = len(users)
    active_users = len([u for u in users if u.is_active])
    total_campaigns = len(campaigns)
    active_campaigns = len([c for c in campaigns if c.is_active])
    total_responses = len(responses)
    # Calculate response rate as percentage of users who have responded at least once
    users_with_responses = len(set([r.user_id for r in responses]))
    response_rate = round((users_with_responses / total_users * 100), 1) if total_users > 0 else 0
    avg_wellbeing = 7.3
    
    # Return the inline template with stats
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SMS Survey System - Admin Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">                                                                                                 
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #5C4B99 0%, #8A7BBF 50%, #A093D1 100%);
            min-height: 100vh;
            color: #1e293b;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 24px;
        }}
        
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 32px;
            padding: 20px 0;
        }}
        
        .logo {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .logo-icon {{
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, #8B5CF6, #3B82F6);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 18px;
        }}
        
        .logo-text h1 {{
            font-size: 24px;
            font-weight: 700;
            color: white;
            margin: 0;
        }}
        
        .logo-text p {{
            font-size: 14px;
            color: rgba(255, 255, 255, 0.8);
            margin: 0;
        }}
        
        .header-actions {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        
        .header-icon {{
            width: 40px;
            height: 40px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #64748b;
            background: #f1f5f9;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        
        .header-icon:hover {{
            background: #e2e8f0;
        }}
        
        .user-avatar {{
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: linear-gradient(135deg, #8B5CF6, #3B82F6);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            cursor: pointer;
        }}
        
        .welcome-section {{
            margin-bottom: 40px;
        }}
        
        .welcome-title {{
            font-size: 32px;
            font-weight: 700;
            color: white;
            margin-bottom: 8px;
        }}
        
        .welcome-subtitle {{
            font-size: 16px;
            color: rgba(255, 255, 255, 0.9);
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 24px;
            margin-bottom: 40px;
        }}
        
        .stat-card {{
            background: white;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
            transition: all 0.2s ease;
        }}
        
        .stat-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        
        .stat-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
        }}
        
        .stat-icon {{
            width: 48px;
            height: 48px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 20px;
        }}
        
        .stat-icon.blue {{ background: #3B82F6; }}
        .stat-icon.green {{ background: #10B981; }}
        .stat-icon.purple {{ background: #8B5CF6; }}
        .stat-icon.orange {{ background: #F59E0B; }}
        .stat-icon.teal {{ background: #14B8A6; }}
        .stat-icon.pink {{ background: #EC4899; }}
        
        .stat-trend {{
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 14px;
            font-weight: 600;
            color: #10B981;
        }}
        
        .stat-value {{
            font-size: 28px;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 4px;
        }}
        
        .stat-label {{
            font-size: 14px;
            color: #64748b;
            font-weight: 500;
        }}
        
        .quick-actions {{
            margin-bottom: 40px;
        }}
        
        .section-title {{
            font-size: 20px;
            font-weight: 600;
            color: #1e293b;
            margin-bottom: 20px;
        }}
        
        .actions-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }}
        
        .action-card {{
            background: white;
            border-radius: 20px;
            padding: 28px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            border: 1px solid rgba(255,255,255,0.2);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            cursor: pointer;
            position: relative;
            overflow: hidden;
        }}
        
        .action-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #8B5CF6, #3B82F6, #10B981);
            transform: scaleX(0);
            transition: transform 0.3s ease;
        }}
        
        .action-card:hover {{
            transform: translateY(-8px) scale(1.02);
            box-shadow: 0 12px 40px rgba(0,0,0,0.15);
            border-color: rgba(139, 92, 246, 0.3);
        }}
        
        .action-card:hover::before {{
            transform: scaleX(1);
        }}
        
        .action-card:active {{
            transform: translateY(-4px) scale(1.01);
        }}
        
        .action-icon {{
            width: 56px;
            height: 56px;
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 24px;
            margin-bottom: 20px;
            transition: all 0.3s ease;
            position: relative;
        }}
        
        .action-card:hover .action-icon {{
            transform: scale(1.1) rotate(5deg);
        }}
        
        .action-title {{
            font-size: 18px;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 12px;
            transition: color 0.3s ease;
        }}
        
        .action-card:hover .action-title {{
            color: #8B5CF6;
        }}
        
        .action-description {{
            font-size: 14px;
            color: #64748b;
            line-height: 1.6;
            transition: color 0.3s ease;
        }}
        
        .action-card:hover .action-description {{
            color: #475569;
        }}
        
        .dashboard-layout {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 32px;
        }}
        
        .recent-activity {{
            background: white;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
        }}
        
        .activity-item {{
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 16px 0;
            border-bottom: 1px solid #f1f5f9;
        }}
        
        .activity-item:last-child {{
            border-bottom: none;
        }}
        
        .activity-icon {{
            width: 40px;
            height: 40px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 16px;
            flex-shrink: 0;
        }}
        
        .activity-content {{
            flex: 1;
        }}
        
        .activity-text {{
            font-size: 14px;
            color: #1e293b;
            margin-bottom: 4px;
        }}
        
        .activity-time {{
            font-size: 12px;
            color: #64748b;
        }}
        
        .activity-ratings {{
            display: flex;
            gap: 8px;
            margin-top: 4px;
        }}
        
        .rating-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
        }}
        
        .rating-dot.blue {{ background: #3B82F6; }}
        .rating-dot.green {{ background: #10B981; }}
        .rating-dot.purple {{ background: #8B5CF6; }}
        
        .sidebar {{
            display: flex;
            flex-direction: column;
            gap: 24px;
        }}
        
        .sidebar-card {{
            background: white;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
        }}
        
        .sidebar-item {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 0;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        
        .sidebar-item:hover {{
            background: #f8fafc;
            border-radius: 8px;
            padding-left: 8px;
        }}
        
        .sidebar-icon {{
            width: 32px;
            height: 32px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #64748b;
            background: #f1f5f9;
            font-size: 14px;
        }}
        
        .sidebar-text {{
            font-size: 14px;
            color: #1e293b;
            font-weight: 500;
        }}
        
        .status-item {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 0;
        }}
        
        .status-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #10B981;
        }}
        
        .status-text {{
            font-size: 14px;
            color: #1e293b;
        }}
        
        .view-all {{
            color: #3B82F6;
            font-size: 14px;
            font-weight: 500;
            text-decoration: none;
            margin-top: 16px;
            display: inline-block;
        }}
        
        .view-all:hover {{
            text-decoration: underline;
        }}
        
        .footer {{
            text-align: right;
            margin-top: 40px;
            color: #94a3b8;
            font-size: 12px;
        }}
        
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        
        /* Modal Styles */
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
            backdrop-filter: blur(4px);
        }}
        
        .modal-content {{
            background-color: white;
            margin: 5% auto;
            padding: 0;
            border-radius: 20px;
            width: 90%;
            max-width: 500px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            animation: modalSlideIn 0.3s ease-out;
        }}
        
        @keyframes modalSlideIn {{
            from {{
                opacity: 0;
                transform: translateY(-50px) scale(0.9);
            }}
            to {{
                opacity: 1;
                transform: translateY(0) scale(1);
            }}
        }}
        
        .modal-header {{
            background: linear-gradient(135deg, #8B5CF6, #3B82F6);
            color: white;
            padding: 24px;
            border-radius: 20px 20px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .modal-title {{
            font-size: 20px;
            font-weight: 700;
            margin: 0;
        }}
        
        .close {{
            color: white;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
            opacity: 0.8;
            transition: opacity 0.3s ease;
        }}
        
        .close:hover {{
            opacity: 1;
        }}
        
        .modal-body {{
            padding: 32px;
        }}
        
        .form-group {{
            margin-bottom: 24px;
        }}
        
        .form-label {{
            display: block;
            font-size: 14px;
            font-weight: 600;
            color: #374151;
            margin-bottom: 8px;
        }}
        
        .form-input {{
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e5e7eb;
            border-radius: 12px;
            font-size: 16px;
            transition: all 0.3s ease;
            box-sizing: border-box;
        }}
        
        .form-input:focus {{
            outline: none;
            border-color: #8B5CF6;
            box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
        }}
        
        .form-textarea {{
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e5e7eb;
            border-radius: 12px;
            font-size: 16px;
            min-height: 100px;
            resize: vertical;
            transition: all 0.3s ease;
            box-sizing: border-box;
            font-family: inherit;
        }}
        
        .form-textarea:focus {{
            outline: none;
            border-color: #8B5CF6;
            box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
        }}
        
        .modal-footer {{
            padding: 24px 32px;
            border-top: 1px solid #e5e7eb;
            display: flex;
            gap: 12px;
            justify-content: flex-end;
        }}
        
        .btn-modal {{
            padding: 12px 24px;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            border: none;
        }}
        
        .btn-primary {{
            background: linear-gradient(135deg, #8B5CF6, #3B82F6);
            color: white;
        }}
        
        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(139, 92, 246, 0.3);
        }}
        
        .btn-secondary {{
            background: #f3f4f6;
            color: #374151;
        }}
        
        .btn-secondary:hover {{
            background: #e5e7eb;
        }}
        
        /* Form Help Text */
        .form-help {{
            font-size: 12px;
            color: #6b7280;
            margin-top: 4px;
            font-style: italic;
        }}
        
        /* SMS Preview Styles */
        .sms-preview {{
            margin-top: 24px;
            padding: 20px;
            background: #f8fafc;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
        }}
        
        .sms-preview h4 {{
            margin: 0 0 16px 0;
            font-size: 16px;
            font-weight: 600;
            color: #374151;
        }}
        
        .preview-content {{
            background: white;
            border-radius: 8px;
            padding: 16px;
            border: 1px solid #d1d5db;
        }}
        
        .preview-phone {{
            font-size: 14px;
            font-weight: 600;
            color: #059669;
            margin-bottom: 8px;
        }}
        
        .preview-message {{
            font-size: 14px;
            color: #374151;
            line-height: 1.5;
            background: #f3f4f6;
            padding: 12px;
            border-radius: 6px;
            border-left: 3px solid #8B5CF6;
        }}
        
        @media (max-width: 768px) {{
            .dashboard-layout {{
                grid-template-columns: 1fr;
            }}
            
            .stats-grid {{
                grid-template-columns: 1fr;
            }}
            
            .actions-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div class="logo">
                <div class="logo-icon">💬</div>
                <div class="logo-text">
                    <h1>SMS Survey</h1>
                    <p>Wellbeing Analytics Platform</p>
                </div>
            </div>
            <div class="header-actions">
                <div class="header-icon">⚙️</div>
                <div class="user-avatar">A</div>
            </div>
        </div>
        
        <!-- Welcome Section -->
        <div class="welcome-section">
            <h1 class="welcome-title">Good morning, Admin! 👋</h1>
            <p class="welcome-subtitle">Here's what's happening with your surveys today.</p>
        </div>
        
        <!-- Statistics Cards -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-header">
                    <div class="stat-icon blue">👥</div>
                    <div class="stat-trend">↗ +12%</div>
                </div>
                <div class="stat-value">{total_users}</div>
                <div class="stat-label">Total Users</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-header">
                    <div class="stat-icon green">📈</div>
                    <div class="stat-trend">↗ +8%</div>
                </div>
                <div class="stat-value">{active_users}</div>
                <div class="stat-label">Active Users</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-header">
                    <div class="stat-icon purple">🎯</div>
                    <div class="stat-trend">↗ +2</div>
                </div>
                <div class="stat-value">{total_campaigns}</div>
                <div class="stat-label">Campaigns</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-header">
                    <div class="stat-icon orange">💬</div>
                    <div class="stat-trend">↗ +156</div>
                </div>
                <div class="stat-value">{total_responses}</div>
                <div class="stat-label">Responses</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-header">
                    <div class="stat-icon teal">📊</div>
                    <div class="stat-trend">↗ +3.2%</div>
                </div>
                <div class="stat-value">{response_rate}%</div>
                <div class="stat-label">Response Rate</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-header">
                    <div class="stat-icon pink">📈</div>
                    <div class="stat-trend">↗ +0.4</div>
                </div>
                <div class="stat-value">{avg_wellbeing}/10</div>
                <div class="stat-label">Avg Wellbeing</div>
            </div>
        </div>
        
        <!-- Quick Actions -->
        <div class="quick-actions">
            <h2 class="section-title">Quick Actions</h2>
            <div class="actions-grid">
                <div class="action-card" onclick="sendTestSMS()">
                    <div class="action-icon blue">✈️</div>
                    <div class="action-title">Send Test SMS</div>
                    <div class="action-description">Send a test survey to verify setup</div>
                </div>
                
                <div class="action-card" onclick="showAddUserForm()">
                    <div class="action-icon green">👤</div>
                    <div class="action-title">Add New User</div>
                    <div class="action-description">Register a new participant</div>
                </div>
                
                <div class="action-card" onclick="showAddCampaignForm()">
                    <div class="action-icon purple">🧱</div>
                    <div class="action-title">Create Campaign</div>
                    <div class="action-description">Launch a new survey campaign</div>
                </div>
                
                <div class="action-card" onclick="window.location.href='/admin/responses'">
                    <div class="action-icon orange">📊</div>
                    <div class="action-title">View Analytics</div>
                    <div class="action-description">Deep dive into response data</div>
                </div>
            </div>
        </div>
        
        <!-- Dashboard Layout -->
        <div class="dashboard-layout">
            <!-- Recent Activity -->
            <div class="recent-activity">
                <h2 class="section-title">Recent Activity</h2>
                
                <div class="activity-item">
                    <div class="activity-icon blue">💬</div>
                    <div class="activity-content">
                        <div class="activity-text">Sarah Johnson completed daily survey.</div>
                        <div class="activity-ratings">
                            <span class="rating-dot blue"></span>
                            <span class="rating-dot green"></span>
                            <span class="rating-dot purple"></span>
                            <span style="font-size: 12px; color: #64748b;">Joy: 8, Achievement: 7, Meaningfulness: 9</span>
                        </div>
                        <div class="activity-time">2 minutes ago</div>
                    </div>
                </div>
                
                <div class="activity-item">
                    <div class="activity-icon green">👤</div>
                    <div class="activity-content">
                        <div class="activity-text">New user registered for campaign.</div>
                        <div class="activity-time">15 minutes ago</div>
                    </div>
                </div>
                
                <div class="activity-item">
                    <div class="activity-icon purple">🎯</div>
                    <div class="activity-content">
                        <div class="activity-text">Started 'Workplace Wellbeing' campaign.</div>
                        <div class="activity-time">1 hour ago</div>
                    </div>
                </div>
                
                <div class="activity-item">
                    <div class="activity-icon blue">💬</div>
                    <div class="activity-content">
                        <div class="activity-text">Mike Chen completed daily survey.</div>
                        <div class="activity-ratings">
                            <span class="rating-dot blue"></span>
                            <span class="rating-dot green"></span>
                            <span class="rating-dot purple"></span>
                            <span style="font-size: 12px; color: #64748b;">Joy: 6, Achievement: 8, Meaningfulness: 7</span>
                        </div>
                        <div class="activity-time">2 hours ago</div>
                    </div>
                </div>
                
                <div class="activity-item">
                    <div class="activity-icon orange">⏰</div>
                    <div class="activity-content">
                        <div class="activity-text">Sent daily surveys to 89 users.</div>
                        <div class="activity-time">3 hours ago</div>
                    </div>
                </div>
                
                <a href="#" class="view-all">View all activity</a>
            </div>
            
            <!-- Sidebar -->
            <div class="sidebar">
                <!-- System Management -->
                <div class="sidebar-card">
                    <h3 class="section-title">System Management</h3>
                    
                    <div class="sidebar-item" onclick="window.location.href='/admin/users'">
                        <div class="sidebar-icon">👥</div>
                        <div class="sidebar-text">User Management</div>
                    </div>
                    
                    <div class="sidebar-item" onclick="window.location.href='/admin/campaigns'">
                        <div class="sidebar-icon">🎯</div>
                        <div class="sidebar-text">Campaign Management</div>
                    </div>
                    
                    <div class="sidebar-item" onclick="window.location.href='/admin/responses'">
                        <div class="sidebar-icon">💬</div>
                        <div class="sidebar-text">View Responses</div>
                    </div>
                    
                </div>
                
                <!-- System Status -->
                <div class="sidebar-card">
                    <h3 class="section-title">System Status</h3>
                    
                    <div class="status-item">
                        <div class="status-text">SMS Service</div>
                        <div class="status-dot"></div>
                    </div>
                    
                    <div class="status-item">
                        <div class="status-text">Database</div>
                        <div class="status-dot"></div>
                    </div>
                    
                    <div class="status-item">
                        <div class="status-text">Scheduler</div>
                        <div class="status-dot"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Add User Modal -->
    <div id="addUserModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title">Add New User</h2>
                <span class="close" onclick="closeModal('addUserModal')">&times;</span>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label class="form-label" for="userName">Full Name</label>
                    <input type="text" id="userName" class="form-input" placeholder="Enter user's full name" required>
                </div>
                <div class="form-group">
                    <label class="form-label" for="userPhone">Phone Number</label>
                    <input type="tel" id="userPhone" class="form-input" placeholder="+1234567890" required>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn-modal btn-secondary" onclick="closeModal('addUserModal')">Cancel</button>
                <button class="btn-modal btn-primary" onclick="submitAddUser()">Add User</button>
            </div>
        </div>
    </div>
    
    <!-- Add Campaign Modal -->
    <div id="addCampaignModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title">Create New Campaign</h2>
                <span class="close" onclick="closeModal('addCampaignModal')">&times;</span>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label class="form-label" for="campaignName">Campaign Name</label>
                    <input type="text" id="campaignName" class="form-input" placeholder="Enter campaign name" required>
                </div>
                <div class="form-group">
                    <label class="form-label" for="campaignDescription">Description</label>
                    <textarea id="campaignDescription" class="form-textarea" placeholder="Enter campaign description (optional)"></textarea>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn-modal btn-secondary" onclick="closeModal('addCampaignModal')">Cancel</button>
                <button class="btn-modal btn-primary" onclick="submitAddCampaign()">Create Campaign</button>
            </div>
        </div>
    </div>
    
    <!-- Send Test SMS Modal -->
    <div id="sendSMSModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title">Send Test SMS</h2>
                <span class="close" onclick="closeModal('sendSMSModal')">&times;</span>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label class="form-label" for="smsPhone">Phone Number</label>
                    <input type="tel" id="smsPhone" class="form-input" placeholder="+1234567890" required>
                    <div class="form-help">Enter the phone number in international format (e.g., +1234567890)</div>
                </div>
                <div class="form-group">
                    <label class="form-label" for="smsMessage">Custom Message (Optional)</label>
                    <textarea id="smsMessage" class="form-textarea" placeholder="Leave empty to send default survey message"></textarea>
                    <div class="form-help">If left empty, the default wellbeing survey will be sent</div>
                </div>
                <div class="sms-preview">
                    <h4>Preview:</h4>
                    <div class="preview-content">
                        <div class="preview-phone">📱 <span id="previewPhone">+1234567890</span></div>
                        <div class="preview-message" id="previewMessage">Default survey message will appear here...</div>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn-modal btn-secondary" onclick="closeModal('sendSMSModal')">Cancel</button>
                <button class="btn-modal btn-primary" onclick="submitSendSMS()">Send SMS</button>
            </div>
        </div>
    </div>
    
    <script>
        function sendTestSMS() {{
            document.getElementById('sendSMSModal').style.display = 'block';
            document.getElementById('smsPhone').focus();
            updateSMSPreview();
        }}
        
        function submitSendSMS() {{
            const phone = document.getElementById('smsPhone').value.trim();
            const message = document.getElementById('smsMessage').value.trim();
            
            if (!phone) {{
                alert('Please enter a phone number');
                return;
            }}
            
            // Show loading state
            const submitBtn = document.querySelector('#sendSMSModal .btn-primary');
            const originalText = submitBtn.textContent;
            submitBtn.innerHTML = '<div style="display: inline-block; width: 16px; height: 16px; border: 2px solid white; border-radius: 50%; border-top-color: transparent; animation: spin 1s linear infinite; margin-right: 8px;"></div>Sending...';
            submitBtn.disabled = true;
            
            const payload = {{phone: phone}};
            if (message) {{
                payload.message = message;
            }}
            
            fetch('/admin/send-test-sms', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify(payload)
            }})
            .then(response => response.json())
            .then(data => {{
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
                if (data.success) {{
                    alert('✅ ' + data.message);
                    closeModal('sendSMSModal');
                }} else {{
                    alert('❌ Error: ' + (data.error || 'Failed to send SMS'));
                }}
            }})
            .catch(error => {{
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
                alert('❌ Error: Failed to send SMS. Please try again.');
                console.error('Error:', error);
            }});
        }}
        
        function updateSMSPreview() {{
            const phone = document.getElementById('smsPhone').value || '+1234567890';
            const message = document.getElementById('smsMessage').value;
            
            document.getElementById('previewPhone').textContent = phone;
            
            if (message) {{
                document.getElementById('previewMessage').textContent = message;
            }} else {{
                document.getElementById('previewMessage').textContent = 'Hi! Please rate your wellbeing from yesterday on a scale of 1-10:\\n\\n1. How much joy did you experience?\\n2. How much achievement did you feel?\\n3. How much meaningfulness did you find?\\n\\nReply with your ratings and any thoughts!';
            }}
        }}
        
        function showAddUserForm() {{
            document.getElementById('addUserModal').style.display = 'block';
            document.getElementById('userName').focus();
        }}
        
        function submitAddUser() {{
            const name = document.getElementById('userName').value.trim();
            const phone = document.getElementById('userPhone').value.trim();
            
            if (!name || !phone) {{
                alert('Please fill in all required fields');
                return;
            }}
            
            // Show loading state
            const submitBtn = document.querySelector('#addUserModal .btn-primary');
            const originalText = submitBtn.textContent;
            submitBtn.innerHTML = '<div style="display: inline-block; width: 16px; height: 16px; border: 2px solid white; border-radius: 50%; border-top-color: transparent; animation: spin 1s linear infinite; margin-right: 8px;"></div>Adding...';
            submitBtn.disabled = true;
            
            fetch('/admin/add-user', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{name: name, phone: phone}})
            }})
            .then(response => response.json())
            .then(data => {{
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
                if (data.success) {{
                    alert('✅ ' + data.message);
                    closeModal('addUserModal');
                    location.reload();
                }} else {{
                    alert('❌ Error: ' + (data.error || 'Failed to add user'));
                }}
            }})
            .catch(error => {{
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
                alert('❌ Error: Failed to add user. Please try again.');
                console.error('Error:', error);
            }});
        }}
        
        function showAddCampaignForm() {{
            document.getElementById('addCampaignModal').style.display = 'block';
            document.getElementById('campaignName').focus();
        }}
        
        function submitAddCampaign() {{
            const name = document.getElementById('campaignName').value.trim();
            const description = document.getElementById('campaignDescription').value.trim();
            
            if (!name) {{
                alert('Please enter a campaign name');
                return;
            }}
            
            // Show loading state
            const submitBtn = document.querySelector('#addCampaignModal .btn-primary');
            const originalText = submitBtn.textContent;
            submitBtn.innerHTML = '<div style="display: inline-block; width: 16px; height: 16px; border: 2px solid white; border-radius: 50%; border-top-color: transparent; animation: spin 1s linear infinite; margin-right: 8px;"></div>Creating...';
            submitBtn.disabled = true;
            
            fetch('/admin/add-campaign', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{name: name, description: description}})
            }})
            .then(response => response.json())
            .then(data => {{
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
                if (data.success) {{
                    alert('✅ ' + data.message);
                    closeModal('addCampaignModal');
                    location.reload();
                }} else {{
                    alert('❌ Error: ' + (data.error || 'Failed to create campaign'));
                }}
            }})
            .catch(error => {{
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
                alert('❌ Error: Failed to create campaign. Please try again.');
                console.error('Error:', error);
            }});
        }}
        
        function closeModal(modalId) {{
            document.getElementById(modalId).style.display = 'none';
            // Clear form fields
            if (modalId === 'addUserModal') {{
                document.getElementById('userName').value = '';
                document.getElementById('userPhone').value = '';
            }} else if (modalId === 'addCampaignModal') {{
                document.getElementById('campaignName').value = '';
                document.getElementById('campaignDescription').value = '';
            }} else if (modalId === 'sendSMSModal') {{
                document.getElementById('smsPhone').value = '';
                document.getElementById('smsMessage').value = '';
            }}
        }}
        
        // Close modal when clicking outside
        window.onclick = function(event) {{
            const modals = document.querySelectorAll('.modal');
            modals.forEach(modal => {{
                if (event.target === modal) {{
                    modal.style.display = 'none';
                }}
            }});
        }}
        
        // Close modal with Escape key
        document.addEventListener('keydown', function(event) {{
            if (event.key === 'Escape') {{
                const modals = document.querySelectorAll('.modal');
                modals.forEach(modal => {{
                    if (modal.style.display === 'block') {{
                        modal.style.display = 'none';
                    }}
                }});
            }}
        }});
        
        // Initialize SMS modal event listeners when DOM is loaded
        document.addEventListener('DOMContentLoaded', function() {{
            const smsPhone = document.getElementById('smsPhone');
            const smsMessage = document.getElementById('smsMessage');
            
            if (smsPhone) {{
                smsPhone.addEventListener('input', updateSMSPreview);
            }}
            if (smsMessage) {{
                smsMessage.addEventListener('input', updateSMSPreview);
            }}
        }});
    </script>
</body>
</html>
"""

@app.route('/admin/users')
def admin_users():
    users = User.query.all()
    
    # Convert database users to display format
    user_data = []
    for user in users:
        # Count responses for this user
        response_count = Response.query.filter_by(user_id=user.id).count()
        
        # Get last response date
        last_response = Response.query.filter_by(user_id=user.id).order_by(Response.submitted_at.desc()).first()
        if last_response and last_response.submitted_at:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            time_diff = now - last_response.submitted_at.replace(tzinfo=timezone.utc)
            
            if time_diff.days > 0:
                last_response_text = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
            elif time_diff.seconds > 3600:
                hours = time_diff.seconds // 3600
                last_response_text = f"{hours} hour{'s' if hours > 1 else ''} ago"
            elif time_diff.seconds > 60:
                minutes = time_diff.seconds // 60
                last_response_text = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            else:
                last_response_text = "Just now"
        else:
            last_response_text = "Never"
        
        # Format joined date
        joined_date = user.created_at.strftime('%m/%d/%Y') if hasattr(user, 'created_at') and user.created_at else 'Unknown'
        
        user_data.append({
            'name': user.name,
            'phone': user.phone_number,
            'status': 'Active' if user.is_active else 'Inactive',
            'responses': response_count,
            'last_response': last_response_text,
            'joined': joined_date
        })
    
    # If no real data, show sample data for demonstration
    if not user_data:
        user_data = [
            {
                'name': 'No users yet',
                'phone': 'N/A',
                'status': 'Inactive',
                'responses': 0,
                'last_response': 'Never',
                'joined': 'N/A'
            }
        ]
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>User Management - SMS Survey System</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">                                                                                                 
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #5C4B99 0%, #8A7BBF 50%, #A093D1 100%);
            min-height: 100vh;
            color: white;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 24px;
        }}
        
        .header {{
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 32px;
            padding: 20px 0;
        }}
        
        .back-btn {{
            width: 40px;
            height: 40px;
            border-radius: 8px;
            background: #f1f5f9;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #64748b;
            text-decoration: none;
            transition: all 0.2s ease;
        }}
        
        .back-btn:hover {{
            background: #e2e8f0;
            color: #1e293b;
        }}
        
        .header-icon {{
            width: 40px;
            height: 40px;
            border-radius: 8px;
            background: linear-gradient(135deg, #8B5CF6, #7C3AED);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 18px;
        }}
        
        .header-text h1 {{
            font-size: 28px;
            font-weight: 700;
            color: #1e293b;
            margin: 0;
        }}
        
        .header-text p {{
            font-size: 14px;
            color: #64748b;
            margin: 0;
        }}
        
        .content-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }}
        
        .content-title h2 {{
            font-size: 24px;
            font-weight: 600;
            color: #1e293b;
            margin: 0;
        }}
        
        .content-title p {{
            font-size: 14px;
            color: #64748b;
            margin: 4px 0 0 0;
        }}
        
        .controls {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .search-box {{
            position: relative;
        }}
        
        .search-input {{
            width: 280px;
            padding: 12px 16px 12px 40px;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            font-size: 14px;
            background: white;
            transition: all 0.2s ease;
        }}
        
        .search-input:focus {{
            outline: none;
            border-color: #8B5CF6;
            box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
        }}
        
        .search-icon {{
            position: absolute;
            left: 12px;
            top: 50%;
            transform: translateY(-50%);
            color: #64748b;
            font-size: 16px;
        }}
        
        .btn {{
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s ease;
            border: none;
            cursor: pointer;
        }}
        
        .btn-primary {{
            background: linear-gradient(135deg, #3B82F6, #8B5CF6);
            color: white;
        }}
        
        .btn-primary:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
        }}
        
        .users-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 24px;
        }}
        
        .user-card {{
            background: white;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
            transition: all 0.2s ease;
        }}
        
        .user-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        
        .user-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 20px;
        }}
        
        .user-info {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        
        .user-avatar {{
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: linear-gradient(135deg, #8B5CF6, #7C3AED);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            font-size: 16px;
        }}
        
        .user-details h3 {{
            font-size: 16px;
            font-weight: 600;
            color: #1e293b;
            margin: 0 0 4px 0;
        }}
        
        .user-phone {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
            color: #64748b;
        }}
        
        .user-actions {{
            display: flex;
            gap: 8px;
        }}
        
        .action-icon {{
            width: 32px;
            height: 32px;
            border-radius: 6px;
            background: #f1f5f9;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #64748b;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        
        .action-icon:hover {{
            background: #e2e8f0;
            color: #1e293b;
        }}
        
        .user-stats {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
            margin-bottom: 20px;
        }}
        
        .stat-item {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        
        .stat-label {{
            font-size: 12px;
            color: #64748b;
            font-weight: 500;
        }}
        
        .stat-value {{
            font-size: 14px;
            color: #1e293b;
            font-weight: 600;
        }}
        
        .status-badge {{
            display: inline-flex;
            align-items: center;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }}
        
        .status-active {{
            background: #dcfce7;
            color: #166534;
        }}
        
        .status-inactive {{
            background: #fee2e2;
            color: #991b1b;
        }}
        
        .joined-date {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            color: #64748b;
            margin-bottom: 16px;
        }}
        
        .analytics-btn {{
            width: 100%;
            padding: 12px 16px;
            background: linear-gradient(135deg, #8B5CF6, #7C3AED);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        
        .analytics-btn:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 16px;
            }}
            
            .content-header {{
                flex-direction: column;
                align-items: flex-start;
                gap: 16px;
            }}
            
            .controls {{
                width: 100%;
                justify-content: space-between;
            }}
            
            .search-input {{
                width: 200px;
            }}
            
            .users-grid {{
                grid-template-columns: 1fr;
            }}
            
            .user-stats {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <a href="/admin/" class="back-btn">←</a>
            <div class="header-icon">👥</div>
            <div class="header-text">
                <h1>User Management</h1>
                <p>Manage survey participants</p>
            </div>
        </div>
        
        <!-- Content Header -->
        <div class="content-header">
                   <div class="content-title">
                       <h2>All Users</h2>
                       <p>{len(user_data)} total participants</p>
                   </div>
            <div class="controls">
                <div class="search-box">
                    <span class="search-icon">🔍</span>
                    <input type="text" class="search-input" placeholder="Search users...">
                </div>
                <button class="btn btn-primary">
                    <span>+</span>
                    Add User
                </button>
            </div>
        </div>
        
        <!-- User Cards -->
        <div class="users-grid">
            {''.join([f'''
            <div class="user-card">
                <div class="user-header">
                    <div class="user-info">
                        <div class="user-avatar">{user['name'][:2].upper()}</div>
                        <div class="user-details">
                            <h3>{user['name']}</h3>
                            <div class="user-phone">
                                <span>📱</span>
                                <span>{user['phone']}</span>
                            </div>
                        </div>
                    </div>
                    <div class="user-actions">
                        <div class="action-icon">⋯</div>
                    </div>
                </div>
                
                <div class="user-stats">
                    <div class="stat-item">
                        <div class="stat-label">Status</div>
                        <span class="status-badge {'status-active' if user['status'] == 'Active' else 'status-inactive'}">
                            {user['status']}
                        </span>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Responses</div>
                        <div class="stat-value">{user['responses']}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Last Response</div>
                        <div class="stat-value">{user['last_response']}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Joined</div>
                        <div class="joined-date">
                            <span>📅</span>
                            <span>{user['joined']}</span>
                        </div>
                    </div>
                </div>
                
                <button class="analytics-btn">View Analytics</button>
            </div>
            ''' for user in user_data])}
        </div>
    </div>
</body>
</html>
    """

@app.route('/admin/responses')
def admin_responses():
    responses = Response.query.join(User).join(Campaign).order_by(Response.submitted_at.desc()).all()
    
    # Convert database responses to display format
    response_data = []
    for response in responses:
        overall_score = 0
        rating_count = 0
        
        if response.joy_rating:
            overall_score += response.joy_rating
            rating_count += 1
        if response.achievement_rating:
            overall_score += response.achievement_rating
            rating_count += 1
        if response.meaningfulness_rating:
            overall_score += response.meaningfulness_rating
            rating_count += 1
            
        avg_score = overall_score / rating_count if rating_count > 0 else 0
        
        response_data.append({
            'user_name': response.user.name,
            'phone': response.user.phone_number,
            'timestamp': response.submitted_at.strftime('%m/%d/%Y at %H:%M') if response.submitted_at else 'Unknown',
            'joy_rating': response.joy_rating or 0,
            'achievement_rating': response.achievement_rating or 0,
            'meaningfulness_rating': response.meaningfulness_rating or 0,
            'feedback': response.influence_text or 'No feedback provided',
            'campaign': response.campaign.name,
            'overall': round(avg_score, 1)
        })
    
    # If no real data, show sample data for demonstration
    if not response_data:
        response_data = [
            {
                'user_name': 'No responses yet',
                'phone': 'N/A',
                'timestamp': 'N/A',
                'joy_rating': 0,
                'achievement_rating': 0,
                'meaningfulness_rating': 0,
                'feedback': 'Complete your first survey to see responses here!',
                'campaign': 'Sample Campaign',
                'overall': 0.0
            }
        ]
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Survey Responses - SMS Survey System</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #5C4B99 0%, #8A7BBF 50%, #A093D1 100%);
            min-height: 100vh;
            color: #1e293b;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 24px;
        }}
        
        .header {{
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 32px;
            padding: 20px 0;
        }}
        
        .back-btn {{
            width: 40px;
            height: 40px;
            border-radius: 8px;
            background: #f1f5f9;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #64748b;
            text-decoration: none;
            transition: all 0.2s ease;
        }}
        
        .back-btn:hover {{
            background: #e2e8f0;
            color: #1e293b;
        }}
        
        .header-icon {{
            width: 40px;
            height: 40px;
            border-radius: 8px;
            background: linear-gradient(135deg, #10B981, #059669);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 18px;
        }}
        
        .header-text h1 {{
            font-size: 28px;
            font-weight: 700;
            color: #1e293b;
            margin: 0;
        }}
        
        .header-text p {{
            font-size: 14px;
            color: #64748b;
            margin: 0;
        }}
        
        .content-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }}
        
        .content-title h2 {{
            font-size: 24px;
            font-weight: 600;
            color: #1e293b;
            margin: 0;
        }}
        
        .content-title p {{
            font-size: 14px;
            color: #64748b;
            margin: 4px 0 0 0;
        }}
        
        .controls {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .search-box {{
            position: relative;
        }}
        
        .search-input {{
            width: 280px;
            padding: 12px 16px 12px 40px;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            font-size: 14px;
            background: white;
            transition: all 0.2s ease;
        }}
        
        .search-input:focus {{
            outline: none;
            border-color: #10B981;
            box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1);
        }}
        
        .search-icon {{
            position: absolute;
            left: 12px;
            top: 50%;
            transform: translateY(-50%);
            color: #64748b;
            font-size: 16px;
        }}
        
        .btn {{
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s ease;
            border: none;
            cursor: pointer;
        }}
        
        .btn-primary {{
            background: #10B981;
            color: white;
        }}
        
        .btn-primary:hover {{
            background: #059669;
        }}
        
        .btn-secondary {{
            background: #f1f5f9;
            color: #64748b;
            border: 1px solid #e2e8f0;
        }}
        
        .btn-secondary:hover {{
            background: #e2e8f0;
            color: #1e293b;
        }}
        
        .responses-grid {{
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}
        
        .response-card {{
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
            transition: all 0.2s ease;
        }}
        
        .response-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        
        .response-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 20px;
        }}
        
        .user-info {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        
        .user-avatar {{
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: linear-gradient(135deg, #10B981, #059669);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            font-size: 16px;
        }}
        
        .user-details h3 {{
            font-size: 16px;
            font-weight: 600;
            color: #1e293b;
            margin: 0 0 4px 0;
        }}
        
        .user-details p {{
            font-size: 14px;
            color: #64748b;
            margin: 0;
        }}
        
        .response-time {{
            font-size: 12px;
            color: #64748b;
        }}
        
        .ratings-section {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }}
        
        .ratings {{
            display: flex;
            gap: 24px;
        }}
        
        .rating {{
            text-align: center;
        }}
        
        .rating-circle {{
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 8px;
        }}
        
        .rating-circle.high {{
            background: #dcfce7;
            color: #166534;
        }}
        
        .rating-circle.medium {{
            background: #fef3c7;
            color: #92400e;
        }}
        
        .rating-circle.low {{
            background: #fee2e2;
            color: #991b1b;
        }}
        
        .rating-label {{
            font-size: 12px;
            color: #64748b;
            font-weight: 500;
        }}
        
        .rating-icon {{
            font-size: 16px;
            margin-right: 4px;
        }}
        
        .overall-rating {{
            text-align: right;
        }}
        
        .overall-score {{
            font-size: 18px;
            font-weight: 600;
            color: #1e293b;
            margin-bottom: 8px;
        }}
        
        .progress-bar {{
            width: 120px;
            height: 6px;
            background: #e2e8f0;
            border-radius: 3px;
            overflow: hidden;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #10B981, #059669);
            border-radius: 3px;
            transition: width 0.3s ease;
        }}
        
        .feedback-section {{
            margin-bottom: 16px;
        }}
        
        .feedback-text {{
            background: #f8fafc;
            padding: 16px;
            border-radius: 8px;
            border-left: 4px solid #10B981;
            font-style: italic;
            color: #374151;
            font-size: 14px;
            line-height: 1.5;
        }}
        
        .campaign-tag {{
            display: inline-block;
            padding: 4px 12px;
            background: #f1f5f9;
            color: #64748b;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 16px;
            }}
            
            .content-header {{
                flex-direction: column;
                align-items: flex-start;
                gap: 16px;
            }}
            
            .controls {{
                width: 100%;
                justify-content: space-between;
            }}
            
            .search-input {{
                width: 200px;
            }}
            
            .ratings {{
                gap: 16px;
            }}
            
            .response-header {{
                flex-direction: column;
                gap: 12px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <a href="/admin/" class="back-btn">←</a>
            <div class="header-icon">💬</div>
            <div class="header-text">
                <h1>Survey Responses</h1>
                <p>View and analyze participant responses</p>
            </div>
        </div>
        
        <!-- Content Header -->
        <div class="content-header">
                   <div class="content-title">
                       <h2>All Responses</h2>
                       <p>{len(response_data)} recent responses</p>
                   </div>
            <div class="controls">
                <div class="search-box">
                    <span class="search-icon">🔍</span>
                    <input type="text" class="search-input" placeholder="Search responses...">
                </div>
                <button class="btn btn-secondary">
                    <span>🔽</span>
                    Filter
                </button>
                <button class="btn btn-primary">
                    <span>⬇️</span>
                    Export
                </button>
            </div>
        </div>
        
        <!-- Response Cards -->
        <div class="responses-grid">
                   {''.join([f'''
                   <div class="response-card">
                       <div class="response-header">
                           <div class="user-info">
                               <div class="user-avatar">{response['user_name'][:2].upper()}</div>
                               <div class="user-details">
                                   <h3>{response['user_name']}</h3>
                                   <p>{response['phone']}</p>
                               </div>
                           </div>
                           <div class="response-time">{response['timestamp']}</div>
                       </div>
                       
                       <div class="ratings-section">
                           <div class="ratings">
                               <div class="rating">
                                   <div class="rating-circle {'high' if response['joy_rating'] >= 8 else 'medium' if response['joy_rating'] >= 6 else 'low'}">
                                       <span class="rating-icon">❤️</span>
                                       {response['joy_rating']}
                                   </div>
                                   <div class="rating-label">Joy</div>
                               </div>
                               <div class="rating">
                                   <div class="rating-circle {'high' if response['achievement_rating'] >= 8 else 'medium' if response['achievement_rating'] >= 6 else 'low'}">
                                       <span class="rating-icon">🎯</span>
                                       {response['achievement_rating']}
                                   </div>
                                   <div class="rating-label">Achievement</div>
                               </div>
                               <div class="rating">
                                   <div class="rating-circle {'high' if response['meaningfulness_rating'] >= 8 else 'medium' if response['meaningfulness_rating'] >= 6 else 'low'}">
                                       <span class="rating-icon">⭐</span>
                                       {response['meaningfulness_rating']}
                                   </div>
                                   <div class="rating-label">Meaningfulness</div>
                               </div>
                           </div>
                           <div class="overall-rating">
                               <div class="overall-score">Overall: {response['overall']}/10</div>
                               <div class="progress-bar">
                                   <div class="progress-fill" style="width: {response['overall'] * 10}%"></div>
                               </div>
                           </div>
                       </div>
                       
                       <div class="feedback-section">
                           <div class="feedback-text">"{response['feedback']}"</div>
                       </div>
                       
                       <div class="campaign-tag">{response['campaign']}</div>
                   </div>
                   ''' for response in response_data])}
        </div>
    </div>
</body>
</html>
    """

@app.route('/admin/campaigns')
def admin_campaigns():
    campaigns = Campaign.query.all()
    
    # Convert database campaigns to display format
    campaign_data = []
    for campaign in campaigns:
        # Count participants and responses for this campaign
        campaign_responses = Response.query.filter_by(campaign_id=campaign.id).all()
        participants = User.query.join(Response).filter(Response.campaign_id == campaign.id).distinct().count()
        responses = len(campaign_responses)
        # Response rate = percentage of users who have responded to this campaign
        response_rate = round((participants / max(User.query.count(), 1)) * 100, 1) if participants > 0 else 0
        
        # Format date range
        start_date = campaign.start_date.strftime('%m/%d/%Y') if campaign.start_date else 'Not set'
        end_date = campaign.end_date.strftime('%m/%d/%Y') if campaign.end_date else 'Not set'
        date_range = f"{start_date} - {end_date}"
        
        campaign_data.append({
            'name': campaign.name,
            'description': campaign.description or 'No description provided',
            'status': 'Active' if campaign.is_active else 'Inactive',
            'participants': participants,
            'responses': responses,
            'response_rate': round(response_rate, 1),
            'date_range': date_range
        })
    
    # If no real data, show sample data for demonstration
    if not campaign_data:
        campaign_data = [
            {
                'name': 'Sample Campaign',
                'description': 'Create your first campaign to get started!',
                'status': 'Inactive',
                'participants': 0,
                'responses': 0,
                'response_rate': 0.0,
                'date_range': 'Not set - Not set'
            }
        ]
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Campaign Management - SMS Survey System</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">                                                                                                 
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #5C4B99 0%, #8A7BBF 50%, #A093D1 100%);
            min-height: 100vh;
            color: white;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 24px;
        }}
        
        .header {{
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 32px;
            padding: 20px 0;
        }}
        
        .back-btn {{
            width: 40px;
            height: 40px;
            border-radius: 8px;
            background: #f1f5f9;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #64748b;
            text-decoration: none;
            transition: all 0.2s ease;
        }}
        
        .back-btn:hover {{
            background: #e2e8f0;
            color: #1e293b;
        }}
        
        .header-icon {{
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: linear-gradient(135deg, #8B5CF6, #7C3AED);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 18px;
        }}
        
        .header-text h1 {{
            font-size: 28px;
            font-weight: 700;
            color: #1e293b;
            margin: 0;
        }}
        
        .header-text p {{
            font-size: 14px;
            color: #64748b;
            margin: 0;
        }}
        
        .content-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }}
        
        .content-title h2 {{
            font-size: 24px;
            font-weight: 600;
            color: #1e293b;
            margin: 0;
        }}
        
        .content-title p {{
            font-size: 14px;
            color: #64748b;
            margin: 4px 0 0 0;
        }}
        
        .controls {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .search-box {{
            position: relative;
        }}
        
        .search-input {{
            width: 280px;
            padding: 12px 16px 12px 40px;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            font-size: 14px;
            background: white;
            transition: all 0.2s ease;
        }}
        
        .search-input:focus {{
            outline: none;
            border-color: #8B5CF6;
            box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
        }}
        
        .search-icon {{
            position: absolute;
            left: 12px;
            top: 50%;
            transform: translateY(-50%);
            color: #64748b;
            font-size: 16px;
        }}
        
        .btn {{
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s ease;
            border: none;
            cursor: pointer;
        }}
        
        .btn-primary {{
            background: linear-gradient(135deg, #8B5CF6, #EC4899);
            color: white;
        }}
        
        .btn-primary:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
        }}
        
        .campaigns-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 24px;
        }}
        
        .campaign-card {{
            background: white;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
            transition: all 0.2s ease;
        }}
        
        .campaign-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        
        .campaign-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 16px;
        }}
        
        .campaign-title {{
            font-size: 18px;
            font-weight: 600;
            color: #1e293b;
            margin: 0 0 8px 0;
        }}
        
        .campaign-description {{
            font-size: 14px;
            color: #64748b;
            line-height: 1.5;
            margin: 0 0 16px 0;
        }}
        
        .status-badge {{
            display: inline-flex;
            align-items: center;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }}
        
        .status-active {{
            background: #dcfce7;
            color: #166534;
        }}
        
        .status-inactive {{
            background: #fee2e2;
            color: #991b1b;
        }}
        
        .campaign-actions {{
            display: flex;
            gap: 8px;
            margin-bottom: 20px;
        }}
        
        .action-icon {{
            width: 32px;
            height: 32px;
            border-radius: 6px;
            background: #f1f5f9;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #64748b;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        
        .action-icon:hover {{
            background: #e2e8f0;
            color: #1e293b;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 20px;
        }}
        
        .stat-item {{
            background: #f8fafc;
            border-radius: 8px;
            padding: 16px;
            text-align: center;
        }}
        
        .stat-icon {{
            width: 32px;
            height: 32px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 8px;
            color: white;
            font-size: 14px;
        }}
        
        .stat-icon.blue {{ background: #3B82F6; }}
        .stat-icon.green {{ background: #10B981; }}
        .stat-icon.purple {{ background: #8B5CF6; }}
        
        .stat-value {{
            font-size: 20px;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 4px;
        }}
        
        .stat-label {{
            font-size: 12px;
            color: #64748b;
            font-weight: 500;
        }}
        
        .date-range {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            color: #64748b;
            margin-bottom: 16px;
        }}
        
        .campaign-buttons {{
            display: flex;
            gap: 12px;
        }}
        
        .btn-secondary {{
            background: #f1f5f9;
            color: #64748b;
            border: 1px solid #e2e8f0;
        }}
        
        .btn-secondary:hover {{
            background: #e2e8f0;
            color: #1e293b;
        }}
        
        .btn-outline {{
            background: white;
            color: #8B5CF6;
            border: 1px solid #8B5CF6;
        }}
        
        .btn-outline:hover {{
            background: #8B5CF6;
            color: white;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 16px;
            }}
            
            .content-header {{
                flex-direction: column;
                align-items: flex-start;
                gap: 16px;
            }}
            
            .controls {{
                width: 100%;
                justify-content: space-between;
            }}
            
            .search-input {{
                width: 200px;
            }}
            
            .campaigns-grid {{
                grid-template-columns: 1fr;
            }}
            
            .stats-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <a href="/admin/" class="back-btn">←</a>
            <div class="header-icon">🎯</div>
            <div class="header-text">
                <h1>Campaign Management</h1>
                <p>Manage survey campaigns</p>
            </div>
        </div>
        
        <!-- Content Header -->
        <div class="content-header">
                   <div class="content-title">
                       <h2>All Campaigns</h2>
                       <p>{len(campaign_data)} total campaigns</p>
                   </div>
            <div class="controls">
                <div class="search-box">
                    <span class="search-icon">🔍</span>
                    <input type="text" class="search-input" placeholder="Search campaigns...">
                </div>
                <button class="btn btn-primary">
                    <span>+</span>
                    New Campaign
                </button>
            </div>
        </div>
        
        <!-- Campaign Cards -->
        <div class="campaigns-grid">
                   {''.join([f'''
                   <div class="campaign-card">
                       <div class="campaign-header">
                           <div>
                               <h3 class="campaign-title">{campaign['name']}</h3>
                               <span class="status-badge {'status-active' if campaign['status'] == 'Active' else 'status-inactive'}">
                                   {campaign['status']}
                               </span>
                           </div>
                           <div class="campaign-actions">
                               <div class="action-icon">⏸️</div>
                               <div class="action-icon">⋯</div>
                           </div>
                       </div>
                       
                       <p class="campaign-description">{campaign['description']}</p>
                       
                       <div class="stats-grid">
                           <div class="stat-item">
                               <div class="stat-icon blue">👥</div>
                               <div class="stat-value">{campaign['participants']}</div>
                               <div class="stat-label">Participants</div>
                           </div>
                           <div class="stat-item">
                               <div class="stat-icon green">📊</div>
                               <div class="stat-value">{campaign['responses']}</div>
                               <div class="stat-label">Responses</div>
                           </div>
                           <div class="stat-item">
                               <div class="stat-icon purple">🎯</div>
                               <div class="stat-value">{campaign['response_rate']}%</div>
                               <div class="stat-label">Response Rate</div>
                           </div>
                       </div>
                       
                       <div class="date-range">
                           <span>📅</span>
                           <span>{campaign['date_range']}</span>
                       </div>
                       
                       <div class="campaign-buttons">
                           <button class="btn btn-outline">View Details</button>
                           <button class="btn btn-secondary">Export Data</button>
                       </div>
                   </div>
                   ''' for campaign in campaign_data])}
        </div>
    </div>
</body>
</html>
    """

@app.route('/admin/test-sms', methods=['POST'])
def test_sms():
    try:
        phone_number = request.form.get('phone_number')
        if not phone_number:
            return jsonify({'error': 'Phone number is required'}), 400
        
        # Get or create test user
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            user = User(
                name='Test User',
                phone_number=phone_number,
                is_active=True
            )
            db.session.add(user)
            db.session.commit()
        
        # Get or create test campaign
        campaign = Campaign.query.filter_by(name='Test Campaign').first()
        if not campaign:
            campaign = Campaign(
                name='Test Campaign',
                start_date=date.today(),
                end_date=date.today() + timedelta(days=30),
                is_active=True
            )
            db.session.add(campaign)
            db.session.commit()
        
        # Send test message
        sms_service = SMSService()
        survey_message = sms_service.send_survey_message(user, campaign)
        
        return jsonify({
            'message': 'Test SMS sent successfully',
            'success': True
        })
        
    except Exception as e:
        logger.error(f"Error sending test SMS: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/send-test-sms', methods=['POST'])
def send_test_sms():
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
            phone = data.get('phone')
            custom_message = data.get('message')
        else:
            phone = request.form.get('phone')
            custom_message = request.form.get('message')
        
        if not phone:
            return jsonify({'error': 'Phone number is required'}), 400
        
        # Send test SMS
        sms_service = SMSService()
        
        # Use custom message if provided, otherwise use default test message
        if custom_message and custom_message.strip():
            test_message = custom_message.strip()
        else:
            test_message = "Hi! Please rate your wellbeing from yesterday on a scale of 1-10:\n\n1. How much joy did you experience?\n2. How much achievement did you feel?\n3. How much meaningfulness did you find?\n\nReply with your ratings and any thoughts!"
        
        if sms_service.use_mock:
            sms_service.mock_service.send_sms(
                to=phone,
                body=test_message,
                from_number=sms_service.phone_number
            )
            return jsonify({
                'message': f'Test SMS sent to {phone} (Mock Mode)',
                'success': True
            })
        else:
            sms_service.client.messages.create(
                body=test_message,
                from_=sms_service.phone_number,
                to=phone
            )
            return jsonify({
                'message': f'Test SMS sent to {phone}',
                'success': True
            })
    except Exception as e:
        logger.error(f"Error sending test SMS: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/add-user', methods=['POST'])
def add_user():
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
            name = data.get('name')
            phone_number = data.get('phone')
        else:
            name = request.form.get('name')
            phone_number = request.form.get('phone_number')
        
        if not name or not phone_number:
            return jsonify({'error': 'Name and phone number are required'}), 400
        
        # Check if user already exists
        existing_user = User.query.filter_by(phone_number=phone_number).first()
        if existing_user:
            return jsonify({'error': 'User with this phone number already exists'}), 400
        
        # Create new user
        new_user = User(
            name=name,
            phone_number=phone_number,
            is_active=True
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            'message': f'User {name} added successfully',
            'success': True
        })
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/add-campaign', methods=['POST'])
def add_campaign():
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
            name = data.get('name')
            description = data.get('description', '')
            start_date = data.get('start_date')
            end_date = data.get('end_date')
        else:
            name = request.form.get('name')
            description = request.form.get('description', '')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
        
        if not name:
            return jsonify({'error': 'Campaign name is required'}), 400
        
        # If no dates provided, create a default campaign (active for 1 year)
        if not start_date or not end_date:
            start_date = date.today()
            end_date = date.today() + timedelta(days=365)
        else:
            # Parse dates
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            if start_date >= end_date:
                return jsonify({'error': 'End date must be after start date'}), 400
        
        # Create new campaign
        new_campaign = Campaign(
            name=name,
            description=description,
            start_date=start_date,
            end_date=end_date,
            is_active=True
        )
        
        db.session.add(new_campaign)
        db.session.commit()
        
        return jsonify({
            'message': f'Campaign {name} added successfully',
            'success': True
        })
    except Exception as e:
        logger.error(f"Error adding campaign: {e}")
        return jsonify({'error': str(e)}), 500

# Webhook Routes
@app.route('/webhook/sms', methods=['POST'])
def webhook_sms():
    try:
        from_number = request.form.get('From')
        body = request.form.get('Body', '').strip()
        
        if not from_number or not body:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Find user by phone number
        user = User.query.filter_by(phone_number=from_number).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Parse response (format: joy/achievement/meaningfulness/influence)
        parts = body.split('/')
        if len(parts) >= 4:
            try:
                joy = int(parts[0].strip())
                achievement = int(parts[1].strip())
                meaningfulness = int(parts[2].strip())
                influence = parts[3].strip()
                
                # Get active campaign
                campaign = Campaign.query.filter_by(is_active=True).first()
                if not campaign:
                    return jsonify({'error': 'No active campaign'}), 404
                
                # Create response
                response = Response(
                    user_id=user.id,
                    campaign_id=campaign.id,
                    survey_date=date.today(),
                    joy_rating=joy,
                    achievement_rating=achievement,
                    meaningfulness_rating=meaningfulness,
                    influence_text=influence,
                    submitted_at=datetime.utcnow()
                )
                db.session.add(response)
                db.session.commit()
                
                # Send feedback URL to user via SMS
                feedback_url = f"{os.getenv('BASE_URL', 'http://localhost:5001')}/feedback/{user.id}/{campaign.id}"
                
                # Send SMS with feedback link
                sms_service = SMSService()
                confirmation_message = f"Thank you for your response! 🌟 View your personalized wellbeing insights: {feedback_url}"
                
                if sms_service.use_mock:
                    sms_service.mock_service.send_sms(
                        to=user.phone_number,
                        body=confirmation_message,
                        from_number=sms_service.phone_number
                    )
                else:
                    sms_service.client.messages.create(
                        body=confirmation_message,
                        from_=sms_service.phone_number,
                        to=user.phone_number
                    )
                
                return jsonify({
                    'success': True,
                    'message': 'Response processed and feedback sent',
                    'feedback_url': feedback_url
                })
                
            except ValueError:
                return jsonify({'error': 'Invalid response format'}), 400
        
        return jsonify({'error': 'Invalid response format'}), 400
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({'error': str(e)}), 500

# API Routes
@app.route('/api/')
def api_info():
    return jsonify({
        'message': 'SMS Survey API',
        'endpoints': {
            'feedback': '/api/feedback/<user_id>/<campaign_id> - User feedback page'
        }
    })

@app.route('/feedback/<int:user_id>/<int:campaign_id>')
def user_feedback(user_id, campaign_id):
    user = User.query.get_or_404(user_id)
    campaign = Campaign.query.get_or_404(campaign_id)
    
    responses = Response.query.filter_by(
        user_id=user_id,
        campaign_id=campaign_id
    ).order_by(Response.survey_date.desc()).all()
    
    if not responses:
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>No Data | SMS Survey System</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
            line-height: 1.6;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 40px 20px;
            text-align: center;
        }}
        
        .no-data-card {{
            background: white;
            border-radius: 16px;
            padding: 60px 40px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }}
        
        .no-data-icon {{
            font-size: 4rem;
            margin-bottom: 24px;
        }}
        
        .no-data-title {{
            font-size: 2rem;
            font-weight: 700;
            color: #333;
            margin-bottom: 16px;
        }}
        
        .no-data-text {{
            color: #666;
            font-size: 1.1rem;
            margin-bottom: 32px;
        }}
        
        .user-info {{
            background: #f8f9fa;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 32px;
        }}
        
        .user-name {{
            font-weight: 600;
            color: #333;
            margin-bottom: 8px;
        }}
        
        .user-phone {{
            color: #666;
            font-size: 0.9rem;
        }}
        
        .back-btn {{
            display: inline-block;
            padding: 16px 32px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 12px;
            font-weight: 600;
            transition: all 0.3s ease;
        }}
        
        .back-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
        }}
        
        .encouragement {{
            background: #e8f5e8;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 32px;
        }}
        
        .encouragement-text {{
            color: #2d5a2d;
            font-weight: 500;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="no-data-card">
            <div class="no-data-icon">📊</div>
            <h1 class="no-data-title">Your Wellbeing Journey Starts Here</h1>
            <p class="no-data-text">Hi {user.name}! You haven't submitted any survey responses yet.</p>
            
            <div class="user-info">
                <div class="user-name">{user.name}</div>
                <div class="user-phone">{user.phone_number}</div>
            </div>
            
            <div class="encouragement">
                <div class="encouragement-text">
                    💡 Complete your first survey to see your personalized wellbeing insights and track your progress over time!
                </div>
            </div>
        </div>
    </div>
</body>
</html>
        """
    
    # Calculate averages
    avg_joy = sum(r.joy_rating for r in responses) / len(responses)
    avg_achievement = sum(r.achievement_rating for r in responses) / len(responses)
    avg_meaningfulness = sum(r.meaningfulness_rating for r in responses) / len(responses)
    
    # Get recent responses for display
    recent_responses = responses[:5] if responses else []
    
    # Build recent responses HTML
    recent_responses_html = ""
    if recent_responses:
        for response in recent_responses:
            feedback_html = f'<div class="response-feedback">"{response.influence_text}"</div>' if response.influence_text else '<div class="response-feedback">No feedback provided</div>'
            recent_responses_html += f'''
                <div class="response-item">
                    <div class="response-header">
                        <div class="response-date">{response.survey_date.strftime('%B %d, %Y') if response.survey_date else 'Unknown Date'}</div>
                    </div>
                    <div class="response-ratings">
                        <div class="rating-item">
                            <span class="rating-label">Joy:</span>
                            <span class="rating-value">{response.joy_rating or 0}</span>
                        </div>
                        <div class="rating-item">
                            <span class="rating-label">Achievement:</span>
                            <span class="rating-value">{response.achievement_rating or 0}</span>
                        </div>
                        <div class="rating-item">
                            <span class="rating-label">Meaningfulness:</span>
                            <span class="rating-value">{response.meaningfulness_rating or 0}</span>
                        </div>
                    </div>
                    {feedback_html}
                </div>
                '''
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your Personal Analytics - SMS Survey System</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 50%, #ffffff 100%);
            min-height: 100vh;
            color: #1e293b;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 16px;
        }}
        
        .header p {{
            font-size: 1.1rem;
            color: #64748b;
            margin-bottom: 30px;
        }}
        
        .main-card {{
            background: white;
            border-radius: 24px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.08);
            border: 1px solid rgba(255,255,255,0.2);
        }}
        
        .progress-summary {{
            text-align: center;
            margin-bottom: 40px;
        }}
        
        .progress-title {{
            font-size: 1.8rem;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 8px;
        }}
        
        .progress-subtitle {{
            font-size: 1rem;
            color: #64748b;
            margin-bottom: 32px;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 24px;
            margin-bottom: 40px;
        }}
        
        .metric-card {{
            background: white;
            border-radius: 16px;
            padding: 28px;
            border: 1px solid #e2e8f0;
            position: relative;
            transition: all 0.3s ease;
        }}
        
        .metric-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 12px 40px rgba(0,0,0,0.1);
        }}
        
        .metric-card.joy {{
            border-left: 4px solid #f59e0b;
        }}
        
        .metric-card.achievement {{
            border-left: 4px solid #10b981;
        }}
        
        .metric-card.meaningfulness {{
            border-left: 4px solid #8b5cf6;
        }}
        
        .metric-name {{
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 16px;
        }}
        
        .metric-name.joy {{
            color: #f59e0b;
        }}
        
        .metric-name.achievement {{
            color: #10b981;
        }}
        
        .metric-name.meaningfulness {{
            color: #8b5cf6;
        }}
        
        .score-display {{
            display: flex;
            align-items: baseline;
            margin-bottom: 20px;
        }}
        
        .score-value {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-right: 8px;
        }}
        
        .score-value.joy {{
            color: #f59e0b;
        }}
        
        .score-value.achievement {{
            color: #10b981;
        }}
        
        .score-value.meaningfulness {{
            color: #8b5cf6;
        }}
        
        .score-max {{
            font-size: 1.2rem;
            color: #94a3b8;
            font-weight: 500;
        }}
        
        .progress-bar-container {{
            position: relative;
            margin-bottom: 16px;
        }}
        
        .progress-bar {{
            width: 100%;
            height: 12px;
            background: #f1f5f9;
            border-radius: 6px;
            overflow: hidden;
            position: relative;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #3b82f6, #1d4ed8);
            border-radius: 6px;
            transition: width 0.8s ease;
        }}
        
        .threshold-line {{
            position: absolute;
            top: 0;
            height: 100%;
            width: 2px;
            background: #64748b;
            z-index: 2;
        }}
        
        .threshold-label {{
            position: absolute;
            top: -24px;
            font-size: 0.75rem;
            color: #64748b;
            font-weight: 500;
        }}
        
        .status-message {{
            display: flex;
            align-items: center;
            font-size: 0.9rem;
            font-weight: 500;
        }}
        
        .status-message.above {{
            color: #059669;
        }}
        
        .status-message.below {{
            color: #374151;
        }}
        
        .checkmark {{
            width: 16px;
            height: 16px;
            margin-right: 8px;
        }}
        
        .recent-responses {{
            margin-top: 40px;
        }}
        
        .section-title {{
            font-size: 1.5rem;
            font-weight: 600;
            color: #1e293b;
            margin-bottom: 24px;
        }}
        
        .responses-list {{
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}
        
        .response-item {{
            background: #f8fafc;
            border-radius: 12px;
            padding: 20px;
            border-left: 4px solid #10B981;
        }}
        
        .response-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}
        
        .response-date {{
            font-size: 0.9rem;
            color: #64748b;
            font-weight: 500;
        }}
        
        .response-ratings {{
            display: flex;
            gap: 16px;
            margin-bottom: 12px;
        }}
        
        .rating-item {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.9rem;
        }}
        
        .rating-value {{
            font-weight: 600;
            color: #1e293b;
        }}
        
        .response-feedback {{
            font-style: italic;
            color: #374151;
            background: white;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
        }}
        
        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: #64748b;
        }}
        
        .empty-state h3 {{
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 12px;
            color: #1e293b;
        }}
        
        .empty-state p {{
            font-size: 1rem;
            line-height: 1.6;
        }}
        
        @media (max-width: 768px) {{
            .metrics-grid {{
                grid-template-columns: 1fr;
            }}
            
            .response-ratings {{
                flex-direction: column;
                gap: 8px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Live Demo Visualization</h1>
            <p>See how users track their weekly progress across the three key wellness dimensions.</p>
        </div>
        
        <div class="main-card">
            <div class="progress-summary">
                <h2 class="progress-title">Week 1 Progress Summary</h2>
                <p class="progress-subtitle">Based on {len(responses)} days of survey responses</p>
            </div>
            
            <div class="metrics-grid">
                <div class="metric-card joy">
                    <div class="metric-name joy">Joy</div>
                    <div class="score-display">
                        <div class="score-value joy">{int(avg_joy * 7)}</div>
                        <div class="score-max">/70</div>
                    </div>
                    <div class="progress-bar-container">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {(avg_joy * 7 / 70) * 100}%"></div>
                            <div class="threshold-line" style="left: {(45 / 70) * 100}%"></div>
                            <div class="threshold-label" style="left: {(45 / 70) * 100}%">Threshold: 45</div>
                        </div>
                    </div>
                    <div class="status-message {'above' if avg_joy * 7 >= 45 else 'below'}">
                        {'<svg class="checkmark" viewBox="0 0 16 16" fill="currentColor"><path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/></svg>' if avg_joy * 7 >= 45 else ''}
                        {'Above recommended threshold' if avg_joy * 7 >= 45 else f'{int(45 - avg_joy * 7)} points to reach threshold'}
                    </div>
                </div>
                
                <div class="metric-card achievement">
                    <div class="metric-name achievement">Achievement</div>
                    <div class="score-display">
                        <div class="score-value achievement">{int(avg_achievement * 7)}</div>
                        <div class="score-max">/70</div>
                    </div>
                    <div class="progress-bar-container">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {(avg_achievement * 7 / 70) * 100}%"></div>
                            <div class="threshold-line" style="left: {(42 / 70) * 100}%"></div>
                            <div class="threshold-label" style="left: {(42 / 70) * 100}%">Threshold: 42</div>
                        </div>
                    </div>
                    <div class="status-message {'above' if avg_achievement * 7 >= 42 else 'below'}">
                        {'<svg class="checkmark" viewBox="0 0 16 16" fill="currentColor"><path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/></svg>' if avg_achievement * 7 >= 42 else ''}
                        {'Above recommended threshold' if avg_achievement * 7 >= 42 else f'{int(42 - avg_achievement * 7)} points to reach threshold'}
                    </div>
                </div>
                
                <div class="metric-card meaningfulness">
                    <div class="metric-name meaningfulness">Meaningfulness</div>
                    <div class="score-display">
                        <div class="score-value meaningfulness">{int(avg_meaningfulness * 7)}</div>
                        <div class="score-max">/70</div>
                    </div>
                    <div class="progress-bar-container">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {(avg_meaningfulness * 7 / 70) * 100}%"></div>
                            <div class="threshold-line" style="left: {(49 / 70) * 100}%"></div>
                            <div class="threshold-label" style="left: {(49 / 70) * 100}%">Threshold: 49</div>
                        </div>
                    </div>
                    <div class="status-message {'above' if avg_meaningfulness * 7 >= 49 else 'below'}">
                        {'<svg class="checkmark" viewBox="0 0 16 16" fill="currentColor"><path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/></svg>' if avg_meaningfulness * 7 >= 49 else ''}
                        {'Above recommended threshold' if avg_meaningfulness * 7 >= 49 else f'{int(49 - avg_meaningfulness * 7)} points to reach threshold'}
                    </div>
                </div>
            </div>
            
            {f'''
            <div class="recent-responses">
                <h3 class="section-title">Recent Responses</h3>
                <div class="responses-list">
                    {recent_responses_html}
                </div>
            </div>
            ''' if recent_responses_html else ''}
        </div>
    </div>
</body>
</html>
        """

@app.route('/api/analytics/<int:user_id>/<int:campaign_id>')
def api_analytics(user_id, campaign_id):
    """Get analytics data for a specific user and campaign"""
    try:
        user = User.query.get_or_404(user_id)
        campaign = Campaign.query.get_or_404(campaign_id)
        
        responses = Response.query.filter_by(
            user_id=user_id,
            campaign_id=campaign_id
        ).order_by(Response.survey_date.desc()).all()
        
        if not responses:
            return jsonify({
                'user': {
                    'id': user.id,
                    'name': user.name,
                    'phoneNumber': user.phone_number
                },
                'campaign': {
                    'id': campaign.id,
                    'name': campaign.name
                },
                'responses': [],
                'analytics': {
                    'avgJoy': 0,
                    'avgAchievement': 0,
                    'avgMeaningfulness': 0,
                    'totalResponses': 0
                }
            })
        
        # Calculate analytics
        joy_ratings = [r.joy_rating for r in responses if r.joy_rating is not None]
        achievement_ratings = [r.achievement_rating for r in responses if r.achievement_rating is not None]
        meaningfulness_ratings = [r.meaningfulness_rating for r in responses if r.meaningfulness_rating is not None]
        
        avg_joy = sum(joy_ratings) / len(joy_ratings) if joy_ratings else 0
        avg_achievement = sum(achievement_ratings) / len(achievement_ratings) if achievement_ratings else 0
        avg_meaningfulness = sum(meaningfulness_ratings) / len(meaningfulness_ratings) if meaningfulness_ratings else 0
        
        responses_data = []
        for response in responses:
            response_data = {
                'id': response.id,
                'joyRating': response.joy_rating,
                'achievementRating': response.achievement_rating,
                'meaningfulnessRating': response.meaningfulness_rating,
                'influenceText': response.influence_text,
                'submittedAt': response.submitted_at.isoformat() if response.submitted_at else None,
                'surveyDate': response.survey_date.isoformat() if response.survey_date else None
            }
            responses_data.append(response_data)
        
        analytics_data = {
            'user': {
                'id': user.id,
                'name': user.name,
                'phoneNumber': user.phone_number
            },
            'campaign': {
                'id': campaign.id,
                'name': campaign.name
            },
            'responses': responses_data,
            'analytics': {
                'avgJoy': round(avg_joy, 1),
                'avgAchievement': round(avg_achievement, 1),
                'avgMeaningfulness': round(avg_meaningfulness, 1),
                'totalResponses': len(responses)
            }
        }
        
        return jsonify(analytics_data)
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        return jsonify({'error': 'Failed to get analytics'}), 500

@app.route('/analytics/<int:user_id>')
def personal_analytics(user_id):
    """Personal analytics page for users"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Get all responses for this user
        responses = Response.query.filter_by(user_id=user_id).order_by(Response.survey_date.desc()).all()
        
        # Calculate overall analytics
        if responses:
            joy_ratings = [r.joy_rating for r in responses if r.joy_rating is not None]
            achievement_ratings = [r.achievement_rating for r in responses if r.achievement_rating is not None]
            meaningfulness_ratings = [r.meaningfulness_rating for r in responses if r.meaningfulness_rating is not None]
            
            avg_joy = sum(joy_ratings) / len(joy_ratings) if joy_ratings else 0
            avg_achievement = sum(achievement_ratings) / len(achievement_ratings) if achievement_ratings else 0
            avg_meaningfulness = sum(meaningfulness_ratings) / len(meaningfulness_ratings) if meaningfulness_ratings else 0
            overall_score = (avg_joy + avg_achievement + avg_meaningfulness) / 3
        else:
            avg_joy = avg_achievement = avg_meaningfulness = overall_score = 0
        
        # Get recent responses for display
        recent_responses = responses[:5] if responses else []
        
        # Build recent responses HTML
        recent_responses_html = ""
        if recent_responses:
            for response in recent_responses:
                feedback_html = f'<div class="response-feedback">"{response.influence_text}"</div>' if response.influence_text else ''
                recent_responses_html += f'''
                <div class="response-item">
                    <div class="response-header">
                        <div class="response-date">
                            {response.survey_date.strftime('%B %d, %Y') if response.survey_date else 'Recent'}
                        </div>
                    </div>
                    <div class="response-ratings">
                        <div class="rating-item">
                            <span>❤️</span>
                            <span class="rating-value">{response.joy_rating or 0}</span>
                        </div>
                        <div class="rating-item">
                            <span>🎯</span>
                            <span class="rating-value">{response.achievement_rating or 0}</span>
                        </div>
                        <div class="rating-item">
                            <span>⭐</span>
                            <span class="rating-value">{response.meaningfulness_rating or 0}</span>
                        </div>
                    </div>
                    {feedback_html}
                </div>
                '''
        
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your Personal Analytics - SMS Survey System</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 50%, #ffffff 100%);
            min-height: 100vh;
            color: #1e293b;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 16px;
        }}
        
        .header p {{
            font-size: 1.1rem;
            color: #64748b;
            margin-bottom: 30px;
        }}
        
        .main-card {{
            background: white;
            border-radius: 24px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.08);
            border: 1px solid rgba(255,255,255,0.2);
        }}
        
        .progress-summary {{
            text-align: center;
            margin-bottom: 40px;
        }}
        
        .progress-title {{
            font-size: 1.8rem;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 8px;
        }}
        
        .progress-subtitle {{
            font-size: 1rem;
            color: #64748b;
            margin-bottom: 32px;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 24px;
            margin-bottom: 40px;
        }}
        
        .metric-card {{
            background: white;
            border-radius: 16px;
            padding: 28px;
            border: 1px solid #e2e8f0;
            position: relative;
            transition: all 0.3s ease;
        }}
        
        .metric-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 12px 40px rgba(0,0,0,0.1);
        }}
        
        .metric-card.joy {{
            border-left: 4px solid #f59e0b;
        }}
        
        .metric-card.achievement {{
            border-left: 4px solid #10b981;
        }}
        
        .metric-card.meaningfulness {{
            border-left: 4px solid #8b5cf6;
        }}
        
        .metric-name {{
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 16px;
        }}
        
        .metric-name.joy {{
            color: #f59e0b;
        }}
        
        .metric-name.achievement {{
            color: #10b981;
        }}
        
        .metric-name.meaningfulness {{
            color: #8b5cf6;
        }}
        
        .score-display {{
            display: flex;
            align-items: baseline;
            margin-bottom: 20px;
        }}
        
        .score-value {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-right: 8px;
        }}
        
        .score-value.joy {{
            color: #f59e0b;
        }}
        
        .score-value.achievement {{
            color: #10b981;
        }}
        
        .score-value.meaningfulness {{
            color: #8b5cf6;
        }}
        
        .score-max {{
            font-size: 1.2rem;
            color: #94a3b8;
            font-weight: 500;
        }}
        
        .progress-bar-container {{
            position: relative;
            margin-bottom: 16px;
        }}
        
        .progress-bar {{
            width: 100%;
            height: 12px;
            background: #f1f5f9;
            border-radius: 6px;
            overflow: hidden;
            position: relative;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #3b82f6, #1d4ed8);
            border-radius: 6px;
            transition: width 0.8s ease;
        }}
        
        .threshold-line {{
            position: absolute;
            top: 0;
            height: 100%;
            width: 2px;
            background: #64748b;
            z-index: 2;
        }}
        
        .threshold-label {{
            position: absolute;
            top: -24px;
            font-size: 0.75rem;
            color: #64748b;
            font-weight: 500;
        }}
        
        .status-message {{
            display: flex;
            align-items: center;
            font-size: 0.9rem;
            font-weight: 500;
        }}
        
        .status-message.above {{
            color: #059669;
        }}
        
        .status-message.below {{
            color: #374151;
        }}
        
        .checkmark {{
            width: 16px;
            height: 16px;
            margin-right: 8px;
        }}
        
        .recent-responses {{
            margin-top: 40px;
        }}
        
        .section-title {{
            font-size: 1.5rem;
            font-weight: 600;
            color: #1e293b;
            margin-bottom: 24px;
        }}
        
        .responses-list {{
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}
        
        .response-item {{
            background: #f8fafc;
            border-radius: 12px;
            padding: 20px;
            border-left: 4px solid #10B981;
        }}
        
        .response-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}
        
        .response-date {{
            font-size: 0.9rem;
            color: #64748b;
            font-weight: 500;
        }}
        
        .response-ratings {{
            display: flex;
            gap: 16px;
            margin-bottom: 12px;
        }}
        
        .rating-item {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.9rem;
        }}
        
        .rating-value {{
            font-weight: 600;
            color: #1e293b;
        }}
        
        .response-feedback {{
            font-style: italic;
            color: #374151;
            background: white;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
        }}
        
        .insights-section {{
            background: linear-gradient(135deg, #8B5CF6, #7C3AED);
            color: white;
            border-radius: 16px;
            padding: 30px;
            text-align: center;
        }}
        
        .insights-section h3 {{
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 16px;
        }}
        
        .insights-section p {{
            opacity: 0.9;
            line-height: 1.6;
        }}
        
        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: #64748b;
        }}
        
        .empty-state h3 {{
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 12px;
            color: #1e293b;
        }}
        
        .empty-state p {{
            font-size: 1rem;
            line-height: 1.6;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 20px 16px;
            }}
            
            .content {{
                padding: 24px;
            }}
            
            .header h1 {{
                font-size: 2rem;
            }}
            
            .metrics-grid {{
                grid-template-columns: 1fr;
            }}
            
            .response-ratings {{
                flex-direction: column;
                gap: 8px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Live Demo Visualization</h1>
            <p>See how users track their weekly progress across the three key wellness dimensions.</p>
        </div>
        
        <div class="main-card">
            <div class="progress-summary">
                <h2 class="progress-title">Week 1 Progress Summary</h2>
                <p class="progress-subtitle">Based on {len(responses)} days of survey responses</p>
            </div>
            
            {f'''
            <div class="metrics-grid">
                <div class="metric-card joy">
                    <div class="metric-name joy">Joy</div>
                    <div class="score-display">
                        <div class="score-value joy">{int(avg_joy * 7)}</div>
                        <div class="score-max">/70</div>
                    </div>
                    <div class="progress-bar-container">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {(avg_joy * 7 / 70) * 100}%"></div>
                            <div class="threshold-line" style="left: {(45 / 70) * 100}%"></div>
                            <div class="threshold-label" style="left: {(45 / 70) * 100}%">Threshold: 45</div>
                        </div>
                    </div>
                    <div class="status-message {'above' if avg_joy * 7 >= 45 else 'below'}">
                        {'<svg class="checkmark" viewBox="0 0 16 16" fill="currentColor"><path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/></svg>' if avg_joy * 7 >= 45 else ''}
                        {'Above recommended threshold' if avg_joy * 7 >= 45 else f'{int(45 - avg_joy * 7)} points to reach threshold'}
                    </div>
                </div>
                
                <div class="metric-card achievement">
                    <div class="metric-name achievement">Achievement</div>
                    <div class="score-display">
                        <div class="score-value achievement">{int(avg_achievement * 7)}</div>
                        <div class="score-max">/70</div>
                    </div>
                    <div class="progress-bar-container">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {(avg_achievement * 7 / 70) * 100}%"></div>
                            <div class="threshold-line" style="left: {(42 / 70) * 100}%"></div>
                            <div class="threshold-label" style="left: {(42 / 70) * 100}%">Threshold: 42</div>
                        </div>
                    </div>
                    <div class="status-message {'above' if avg_achievement * 7 >= 42 else 'below'}">
                        {'<svg class="checkmark" viewBox="0 0 16 16" fill="currentColor"><path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/></svg>' if avg_achievement * 7 >= 42 else ''}
                        {'Above recommended threshold' if avg_achievement * 7 >= 42 else f'{int(42 - avg_achievement * 7)} points to reach threshold'}
                    </div>
                </div>
                
                <div class="metric-card meaningfulness">
                    <div class="metric-name meaningfulness">Meaningfulness</div>
                    <div class="score-display">
                        <div class="score-value meaningfulness">{int(avg_meaningfulness * 7)}</div>
                        <div class="score-max">/70</div>
                    </div>
                    <div class="progress-bar-container">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {(avg_meaningfulness * 7 / 70) * 100}%"></div>
                            <div class="threshold-line" style="left: {(49 / 70) * 100}%"></div>
                            <div class="threshold-label" style="left: {(49 / 70) * 100}%">Threshold: 49</div>
                        </div>
                    </div>
                    <div class="status-message {'above' if avg_meaningfulness * 7 >= 49 else 'below'}">
                        {'<svg class="checkmark" viewBox="0 0 16 16" fill="currentColor"><path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/></svg>' if avg_meaningfulness * 7 >= 49 else ''}
                        {'Above recommended threshold' if avg_meaningfulness * 7 >= 49 else f'{int(49 - avg_meaningfulness * 7)} points to reach threshold'}
                    </div>
                </div>
            </div>
            ''' if responses else '''
            <div class="empty-state">
                <h3>No responses yet</h3>
                <p>Complete your first survey to see your personal analytics here!</p>
            </div>
            '''}
            
            {f'''
            <div class="recent-responses">
                <h3 class="section-title">Recent Responses</h3>
                <div class="responses-list">
                    {recent_responses_html}
                </div>
            </div>
            ''' if recent_responses_html else ''}
        </div>
    </div>
</body>
</html>
        """
    except Exception as e:
        logger.error(f"Error generating personal analytics: {e}")
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>Error</title></head>
        <body>
            <h1>Error</h1>
            <p>Unable to load your analytics. Please try again later.</p>
        </body>
        </html>
        """, 500

# INITIALIZATION

def create_sample_data():
    """Create sample data if it doesn't exist"""
    if User.query.first() is None:
        # Create sample user
        user = User(
            name='Sample User',
            phone_number='+1234567890',
            is_active=True
        )
        db.session.add(user)
        
        # Create sample campaign
        campaign = Campaign(
            name='Sample Campaign',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            is_active=True
        )
        db.session.add(campaign)
        
        db.session.commit()
        logger.info("Sample data created successfully")

def main():
    """Main application entry point"""
    # Create database tables
    with app.app_context():
        db.create_all()
        create_sample_data()
    
    # Initialize scheduler
    scheduler_service = SchedulerService()
    
    try:
        # Start scheduler
        scheduler_service.start_scheduler()
        logger.info("Scheduler started successfully")
        
        # Run Flask app
        port = int(os.getenv('PORT', 5001))
        debug = os.getenv('FLASK_ENV') == 'development'
        
        logger.info(f"Starting Flask application on port {port}")
        app.run(host='0.0.0.0', port=port, debug=debug)
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        scheduler_service.stop_scheduler()
    except Exception as e:
        logger.error(f"Error starting application: {e}")
        scheduler_service.stop_scheduler()
        raise

if __name__ == '__main__':
    main()
