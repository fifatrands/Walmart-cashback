import os, re, json, requests, base64, hashlib, hmac, time
from datetime import datetime, timedelta
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///walmart_cashback.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ---------- MODELS ----------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True)
    ibotta_token = db.Column(db.String(200))  # optional
    fetch_token = db.Column(db.String(200))
    push_enabled = db.Column(db.Boolean, default=True)
    email_enabled = db.Column(db.Boolean, default=True)

class Receipt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    filename = db.Column(db.String(200))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    total_cashback = db.Column(db.Float, default=0.0)
    items_json = db.Column(db.Text)  # JSON list of items with prices

class Offer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(100))
    cashback = db.Column(db.Float, nullable=False)
    size = db.Column(db.String(50))
    source = db.Column(db.String(20), default='system')  # 'system' only
    approved = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Create tables
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ---------- HELPER FUNCTIONS ----------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png','jpg','jpeg','gif','pdf'}

def extract_text_from_image(path):
    # OCR functionality temporarily disabled - returning placeholder
    # TODO: Implement OCR service or use cloud-based OCR API
    return "Receipt text extraction temporarily disabled. Please enter items manually."

def extract_text_from_pdf(path):
    # PDF OCR functionality temporarily disabled - returning placeholder
    # TODO: Implement PDF parsing or use cloud-based OCR API
    return "PDF text extraction temporarily disabled. Please upload image files instead."

def parse_receipt(text):
    lines = text.split('\n')
    items = []
    for line in lines:
        if re.search(r'\$\d+\.\d{2}', line):
            parts = re.split(r'\s+', line)
            price = None
            product_parts = []
            for p in parts:
                if re.match(r'\$\d+\.\d{2}', p):
                    price = float(p.replace('$', ''))
                else:
                    product_parts.append(p)
            if price:
                product = ' '.join(product_parts).strip().lower()
                items.append((product, price))
    return items

def calculate_cashback(items, offer_list):
    total = 0.0
    matches = []
    for product, price in items:
        for offer in offer_list:
            if offer.keyword in product:
                cash = offer.cashback
                total += cash
                matches.append({
                    'product': product,
                    'brand': offer.brand,
                    'cashback': cash,
                    'price': price,
                    'offer_id': offer.id
                })
                break
    return total, matches

# ---------- AUTO-SUBMIT (Ibotta/Fetch Mock) ----------
def submit_to_ibotta(items, user_token):
    """Mock API call – replace with real Ibotta endpoints"""
    # In reality, you'd POST to https://api.ibotta.com/v1/receipts
    # with your token and items.
    print(f"Submitting to Ibotta for user {user_token}: {items}")
    return {"status": "success", "message": "Submitted"}

def submit_to_fetch(items, user_token):
    print(f"Submitting to Fetch for user {user_token}: {items}")
    return {"status": "success"}

# ---------- ROUTES ----------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        hashed = generate_password_hash(password)
        user = User(username=username, password_hash=hashed, email=email)
        db.session.add(user)
        db.session.commit()
        flash('Account created – please login')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    receipts = Receipt.query.filter_by(user_id=current_user.id).order_by(Receipt.uploaded_at.desc()).all()
    total_saved = sum(r.total_cashback for r in receipts)
    offers = Offer.query.filter_by(approved=True).all()
    return render_template('dashboard.html', receipts=receipts, total_saved=total_saved, offers=offers)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_receipt():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            # OCR
            if filename.lower().endswith('.pdf'):
                text = extract_text_from_pdf(filepath)
            else:
                text = extract_text_from_image(filepath)
            items = parse_receipt(text)
            # Get all active offers (system only)
            offers = Offer.query.filter_by(approved=True).all()
            total, matches = calculate_cashback(items, offers)
            # Save receipt
            receipt = Receipt(
                user_id=current_user.id,
                filename=filename,
                total_cashback=total,
                items_json=json.dumps(items)
            )
            db.session.add(receipt)
            db.session.commit()
            # Auto-submit if tokens exist
            if current_user.ibotta_token:
                result = submit_to_ibotta_real(matches, current_user.ibotta_token)
                if result.get('status') == 'error':
                    flash(f'Ibotta submission failed: {result.get("message")}')
                else:
                    flash('Submitted to Ibotta!')
            if current_user.fetch_token:
                result = submit_to_fetch_real(matches, current_user.fetch_token)
                if result.get('status') == 'error':
                    flash(f'Fetch submission failed: {result.get("message")}')
                else:
                    flash('Submitted to Fetch Rewards!')
            flash(f'Receipt processed! You earned ${total:.2f} cashback.')
            return render_template('result.html', matches=matches, total=total, items=items)
    return render_template('upload.html')

@app.route('/api/receipts', methods=['GET'])
@login_required
def api_receipts():
    # For mobile app
    receipts = Receipt.query.filter_by(user_id=current_user.id).all()
    data = [{
        'id': r.id,
        'filename': r.filename,
        'total_cashback': r.total_cashback,
        'date': r.uploaded_at.isoformat()
    } for r in receipts]
    return jsonify(data)

# ---------- SETTINGS ----------
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        # Handle token updates
        ibotta_token = request.form.get('ibotta_token', '').strip()
        fetch_token = request.form.get('fetch_token', '').strip()
        
        if ibotta_token:
            current_user.ibotta_token = ibotta_token
        if fetch_token:
            current_user.fetch_token = fetch_token
        
        db.session.commit()
        flash('Settings saved!')
        return redirect(url_for('settings'))
    
    return render_template('settings.html')

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    current_pw = request.form['current_password']
    new_pw = request.form['new_password']
    confirm_pw = request.form['confirm_password']
    
    if not check_password_hash(current_user.password_hash, current_pw):
        flash('Current password is incorrect')
        return redirect(url_for('settings'))
    
    if new_pw != confirm_pw:
        flash('New passwords do not match')
        return redirect(url_for('settings'))
    
    if len(new_pw) < 8:
        flash('Password must be at least 8 characters')
        return redirect(url_for('settings'))
    
    current_user.password_hash = generate_password_hash(new_pw)
    db.session.commit()
    flash('Password changed successfully!')
    return redirect(url_for('settings'))

# ---------- REAL API STUBS ----------
def submit_to_ibotta_real(items, user_token):
    """Real Ibotta API integration - replace with actual endpoints"""
    # Ibotta Partner API (requires approval)
    # POST https://api.ibotta.com/v1/receipts
    # Headers: Authorization: Bearer *** Content-Type: application/json
    # Body: { "receipt": { "items": [...], "retailer": "walmart", "date": "..." } }
    
    headers = {
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "receipt": {
            "items": [
                {
                    "description": item['product'],
                    "price": item['price'],
                    "quantity": 1,
                    "brand": item.get('brand', ''),
                    "cashback": item['cashback']
                }
                for item in items
            ],
            "retailer": "walmart",
            "date": datetime.utcnow().isoformat()
        }
    }
    
    try:
        resp = requests.post(
            "https://api.ibotta.com/v1/receipts",
            json=payload,
            headers=headers,
            timeout=30
        )
        return resp.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def submit_to_fetch_real(items, user_token):
    """Real Fetch Rewards API integration - replace with actual endpoints"""
    # Fetch Rewards API (requires approval)
    # POST https://api.fetchrewards.com/v1/receipts
    
    headers = {
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "items": [
            {
                "description": item['product'],
                "price": item['price'],
                "brand": item.get('brand', ''),
                "rewards": item['cashback']
            }
            for item in items
        ],
        "retailer": "walmart",
        "purchase_date": datetime.utcnow().isoformat()
    }
    
    try:
        resp = requests.post(
            "https://api.fetchrewards.com/v1/receipts",
            json=payload,
            headers=headers,
            timeout=30
        )
        return resp.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ---------- PWA MANIFEST ----------
@app.route('/manifest.json')
def manifest():
    return {
        "name": "Walmart Cashback",
        "short_name": "WallyCash",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#0071dc",
        "icons": [{"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"}]
    }

# ---------- RUN ----------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)