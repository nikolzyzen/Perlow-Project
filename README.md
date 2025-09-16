# SMS Survey System Prototype

## **Setup**

To run the program, simply enter:
```bash 
python start.py
```
This will automatically:
- Create a virtual environment 
- Install all required dependencies
- Resolve any port conflicts
- Start the application at http://localhost:5001

**Access points:**

- Admin Dashboard: http://localhost:5001/admin/ - Main admin interface with statistics and quick actions
- User Management: http://localhost:5001/admin/users - View and manage all users
- Campaign Management: http://localhost:5001/admin/campaigns - View and manage all campaigns
- Responses View: http://localhost:5001/admin/responses - View all survey responses
- Personal Analytics: http://localhost:5001/analytics/1 - Individual user's wellbeing insights
- User Feedback: http://localhost:5001/feedback/1/1 - Page sent to users via SMS after responding

- API Stats: http://localhost:5001/api/stats - System statistics in JSON format
- API Users: http://localhost:5001/api/users - All users data in JSON format
- API Campaigns: http://localhost:5001/api/campaigns - All campaigns data in JSON format
- API Responses: http://localhost:5001/api/responses - Recent responses in JSON format
- API Analytics: http://localhost:5001/api/analytics/1/1 - Specific user analytics in JSON format

## **System Overview**

This application measures three dimensions of well-being (joy, achievement, and meaningfulness) through daily SMS surveys powered by Twilio. Responses are processed instantly and displayed on a modern admin dashboard, giving users personal insights and progress tracking. The system includes smart scheduling with APScheduler to automate survey delivery and a mock mode that allows cost-free testing without sending real SMS.


## **Architecture Overview**

```
┌─────────────────────────────────────────────────────────────────┐
│                    SMS Survey System                            │
├─────────────────────────────────────────────────────────────────┤
│     SMS Layer               Web Layer           Analytics      │
│  ┌─────────────┐      ┌─────────────────┐    ┌─────────────┐    │
│  │   Twilio    │◄────►│  React Frontend │◄──►│  Personal   │    │
│  │   SMS API   │      │  (TypeScript)   │    │ Dashboard   │    │
│  └─────────────┘      └─────────────────┘    └─────────────┘    │
│         │                      │                     │          │
│         ▼                      ▼                     ▼          │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                Flask Backend (Python)                      │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │ │
│  │  │SMS Service  │ │ API Routes  │ │  Admin Interface    │   │ │
│  │  │(Mock/Real)  │ │(REST API)   │ │ (Server-rendered)   │   │ │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘   │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              SQLite Database (survey.db)                   │ │
│  │ ┌─────────┐ ┌─────────────┐ ┌──────────┐ ┌─────────────┐   │ │
│  │ │  Users  │ │ Campaigns   │ │Response  │ │   Survey    │   │ │
│  │ │ Table   │ │   Table     │ │ Table    │ │  Messages   │   │ │
│  │ └─────────┘ └─────────────┘ └──────────┘ └─────────────┘   │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## **Project Structure**

```
sms_survey_system/
├── sms_survey.py              # Main Flask application
├── start.py                   # Setup + start
├── requirements.txt           # Python dependencies
├── README.md                  # This documentation
│
├── instance/                  # Flask instance folder
│   └── survey.db                 # SQLite database
│
├── venv/                      # Python virtual environment 
│   ├── bin/                      # Python executables
│   ├── lib/                      # Installed packages
│   └── pyvenv.cfg               # Environment configuration
│
└── src/                       # React frontend source code
    ├── App.tsx                   # Main React app component
    ├── main.tsx                  # React entry point
    ├── index.css                 # Global styles
    └── components/               # React components
        ├── AdminDashboard.tsx    # Main admin interface
        ├── PersonalAnalytics.tsx # User analytics dashboard
        ├── UserManagement.tsx    # User CRUD operations
        ├── CampaignManagement.tsx# Campaign CRUD operations
        ├── ResponsesView.tsx     # Survey responses display
        ├── StatsCard.tsx         # Reusable statistics widget
        ├── QuickActionCard.tsx   # Action button component
        └── RecentActivity.tsx    # Activity feed component
```

## **Database Schema**

### **Entity Relationships**
```
Users ↔ Campaigns (Many-to-Many via Responses)
  │         │
  ▼         ▼
Responses (Junction Table + Data)
  │
  ▼
Survey Messages (Delivery Tracking)
```

## **API Endpoints**

### **Statistics & Analytics**
| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/api/stats` | GET | Dashboard overview | User/campaign/response counts |
| `/api/analytics/<user_id>/<campaign_id>` | GET | Personal analytics | Individual insights & trends |

### **Data Management**  
| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/api/users` | GET | List all users | Users with response counts |
| `/api/campaigns` | GET | List campaigns | Campaigns with statistics |
| `/api/responses` | GET | List responses | All survey submissions |

### **Administrative Actions**
| Endpoint | Method | Purpose | Body |
|----------|--------|---------|------|
| `/admin/add-user` | POST | Create user | `{name, phone_number}` |
| `/admin/add-campaign` | POST | Create campaign | `{name, description, dates}` |
| `/admin/test-sms` | POST | Send test SMS | `{phone_number, message}` |

### **SMS Integration**
| Endpoint | Method | Purpose | Notes |
|----------|--------|---------|-------|
| `/webhook/sms` | POST | Twilio webhook | Parses "8/7/9/text" format |
| `/feedback/<user_id>/<campaign_id>` | GET | Personal analytics page | User-facing HTML |


### **Sample Survey Message**
```
Hi Sarah! 

Daily Wellbeing Check-in for September 15, 2024:

Please rate your day yesterday (1-10):
1. Joy: How much joy did you get?
2. Achievement: How much achievement did you get?
3. Meaningfulness: How much meaningfulness did you get?
4. Influence: What influenced your ratings most?

Reply with: joy/achievement/meaningfulness/influence
Example: 8/7/9/Spent time with family

Thank you for participating! 💙
```

## **Technology Stack Choice**

Given the short development timeline, I built a rough prototype meant as a starting point rather than something ready for deployment. I also want to acknowledge the use of the Claude-4-Sonnet model, which helped me write and debug parts of the code.

For the backend, I chose Python with Flask because it’s lightweight and well-suited for building APIs, while still leaving room to integrate analytics or data science later. SQLite with SQLAlchemy provides an easy, no-setup database during development, while keeping the flexibility to migrate to a more robust system if needed.

For communication, the Twilio SMS API handles sending and receiving texts, offloading infrastructure complexity. Paired with APScheduler, it enables automated daily surveys and background tasks without extra services.

On the front end, I used React with TypeScript for productivity and maintainability, Vite for fast builds and a smooth dev experience, and Tailwind CSS for efficient, responsive styling without the overhead of a custom design system.

That said, the current system isn’t production-ready. The backend would likely need to be rewritten in C# with PostgreSQL, since that combination is better suited for caching, optimization, and handling higher traffic. It would also require a more detailed database schema, well-structured business logic, and properly defined endpoints—areas that would demand significantly more design and planning time.

I also encountered limitations with Twilio. Sending real messages requires a verified business account and incurs per-message costs, which I couldn’t set up without assistance. To work around this, I implemented a Mock SMS mode that simulates sending and receiving texts by logging them to the console. This allows end-to-end testing of survey delivery, response handling, and webhooks without relying on paid SMS.

In production, the mock mode would need to be disabled with proper configuration:
```bash
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone
USE_MOCK_SMS=false
FLASK_ENV=production
SECRET_KEY=your-secure-secret-key
PORT=5001
DATABASE_URL=sqlite:///survey.db
BASE_URL=https://yourdomain.com
```

Finally, the frontend pulls live data through API endpoints for admin pages, user analytics, and campaign views. However, some data is still intentionally hardcoded—sample responses, fallback content, and placeholders—to keep the interface consistent, support testing, and ensure it never appears empty.


