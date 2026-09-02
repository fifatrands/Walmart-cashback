# Walmart Cashback Engine 3.0

A fully integrated cashback system with auto-submit to Ibotta/Fetch, price alerts, crowdsourced offers, and a PWA mobile app.

## Features

- 📸 **Receipt OCR** - Upload receipts (image/PDF), extract items via Tesseract
- 💰 **Auto Cashback Matching** - Matches items against crowdsourced offers database
- 🔔 **Price Drop Alerts** - Monitors Walmart prices, alerts when prices drop below target
- 👥 **Crowdsourced Offers** - Community-submitted offers, validated and shared
- 🤖 **Auto-Submit** - Mock hooks for Ibotta/Fetch (plug in real API keys)
- 📱 **PWA Mobile App** - Installable on iOS/Android, works offline with Service Worker
- 🔐 **User Accounts** - Secure login with Flask-Login

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Install system dependencies (Ubuntu/Debian)
sudo apt update && sudo apt install -y tesseract-ocr poppler-utils

# Run
python app.py

# Visit http://localhost:5000
```

## Default Admin

- Username: `admin`
- Password: `admin123`

## Project Structure

```
walmart_cashback/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── walmart_cashback.db # SQLite database
├── templates/          # Jinja2 templates
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── upload.html
│   └── result.html
├── static/             # Static assets
│   ├── sw.js          # Service Worker
│   └── icon-192.png   # PWA icon
└── uploads/           # Uploaded receipts
```

## Deployment (Render.com)

1. Push to GitHub
2. Create Web Service on Render
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn app:app`
5. Add PostgreSQL database
6. Update `SQLALCHEMY_DATABASE_URI` in app.py

## API Endpoints

- `GET /api/receipts` - JSON list of user's receipts (for mobile app)
- `POST /upload` - Upload receipt (multipart/form-data)
- `POST /create_alert` - Create price alert
- `POST /add_offer` - Add crowdsourced offer

## Real API Integration

Replace mock functions in `app.py`:

```python
def submit_to_ibotta(items, user_token):
    # POST to https://api.ibotta.com/v1/receipts with token
    pass

def submit_to_fetch(items, user_token):
    # POST to Fetch Rewards API
    pass
```

Add user tokens via profile settings or admin panel.