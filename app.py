from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.utils import secure_filename
import os
import random
from datetime import datetime, timedelta
import requests  # For Unsplash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'fallback_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'txt'}

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
socketio = SocketIO(app, cors_allowed_origins="*")  # CORS for SocketIO

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Import models after db
from models import db, User, Chat, Transaction, Referral, Notification, GameLog

with app.app_context():
    db.create_all()
    # Create default admin if not exists (fixed: ensure is_admin)
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@example.com', password_hash=generate_password_hash('adminpass'), is_admin=True, balance=999999, vip=True, last_login=datetime.now())
        db.session.add(admin)
        db.session.commit()
        flash('Default admin created: admin/adminpass')  # Temp flash

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Unsplash Route for Gaming Images
@app.route('/api/image/<category>')
def get_unsplash_image(category='gaming'):
    access_key = os.getenv('UNSPLASH_ACCESS_KEY')
    if not access_key:
        return jsonify({'error': 'API key not set'}), 500
    url = f"https://api.unsplash.com/photos/random?query={category}&client_id={access_key}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return jsonify({'url': data['urls']['regular'], 'alt': data['alt_description']})
    return jsonify({'error': 'Image fetch failed'}), 500

# Home (add image)
@app.route('/')
def index():
    image = requests.get('http://127.0.0.1:5000/api/image/gaming').json() if os.getenv('UNSPLASH_ACCESS_KEY') else {'url': 'https://via.placeholder.com/800x400?text=Gaming+Hero'}
    return render_template('index.html', user=current_user if current_user.is_authenticated else None, hero_image=image)

# Login (fixed: add banned check)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            if user.banned:
                flash('Account banned. Contact admin.', 'error')
                return render_template('login.html')
            login_user(user)
            user.last_login = datetime.now()
            # Daily reward
            if user.last_login < datetime.now() - timedelta(days=1):
                user.balance += 50
                send_notification(user.id, 'Daily login bonus: +50 coins!')
                flash('Daily login bonus: +50 coins!', 'success')
            db.session.commit()
            return redirect(url_for('index'))
        flash('Invalid credentials', 'error')
    return render_template('login.html')

# Signup (same as before, but add notification)
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # ... (same code as before)
        # After commit
        send_notification(user.id, 'Welcome! Starter balance: 100 coins')
        flash('Signup successful! Welcome bonus added.', 'success')
    return render_template('signup.html')

# ... (other routes like logout, profile call get_transactions below)

# Profile (updated: show transactions)
@app.route('/profile/<userid>')
@login_required
def profile(userid):
    user = User.query.filter_by(userid=userid).first_or_404()
    transactions = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.timestamp.desc()).all()  # Show trans
    notifications = Notification.query.filter_by(user_id=user.id, read=False).all()  # Unread notifs
    return render_template('profile.html', profile_user=user, transactions=transactions, notifications=notifications)

# Deposit (fixed: proper calc, utr from form, status pending)
@app.route('/deposit', methods=['POST'])
@login_required
def deposit():
    amount = float(request.form['amount'])
    utr = request.form.get('utr', '')  # Add UTR field in form
    if 20 <= amount <= 1000:
        fee = amount * 0.1
        net = amount - fee
        if amount > 500:
            net += amount * 0.15  # Bonus
        trans = Transaction(user_id=current_user.id, type='deposit', amount=net, utr=utr, status='pending', fee=fee, timestamp=datetime.now())
        db.session.add(trans)
        db.session.commit()
        send_notification(current_user.id, f'Deposit {amount} pending approval. Net: {net}')
        flash('Yay! Your Deposit is On The Way. Please Wait. We Will Verify In Some Hours.', 'success')
    else:
        flash('Invalid amount: Min 20, Max 1000', 'error')
    return redirect(url_for('profile', userid=current_user.userid))

# Withdraw (fixed: daily limit check, no cancel, charge)
@app.route('/withdraw', methods=['POST'])
@login_required
def withdraw():
    amount = float(request.form['amount'])
    today_withdraws = Transaction.query.filter_by(user_id=current_user.id, type='withdraw').filter(Transaction.timestamp > datetime.now() - timedelta(days=1)).count()
    if current_user.balance >= amount and today_withdraws < 2:
        fee = amount * 0.2
        net = amount - fee
        trans = Transaction(user_id=current_user.id, type='withdraw', amount=net, status='pending', fee=fee, timestamp=datetime.now())
        db.session.add(trans)
        current_user.balance -= amount  # Lock
        db.session.commit()
        send_notification(current_user.id, f'Withdraw {amount} requested. Net: {net} (20% fee). Cannot cancel.')
        flash('Withdrawal request submitted. Processed soon. (No cancel)', 'success')
    else:
        flash('Insufficient balance or daily limit (2/day) exceeded', 'error')
    return redirect(url_for('profile', userid=current_user.userid))

# Notifications Page
@app.route('/notifications')
@login_required
def notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.timestamp.desc()).all()
    for n in notifs:
        n.read = True
    db.session.commit()
    return render_template('notifications.html', notifications=notifs)

def send_notification(user_id, msg):
    notif = Notification(user_id=user_id, message=msg)
    db.session.add(notif)
    db.session.commit()

# Admin (fixed: stronger check, pro UI with tables)
@app.route('/s/s/secret/1/000/admin/ap', methods=['GET', 'POST'])
@login_required
def admin():
    if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
        flash('Access denied. Admin only.', 'error')
        return redirect(url_for('index'))
    users = User.query.all()
    transactions = Transaction.query.all()
    chats = Chat.query.all()
    logs = GameLog.query.all()
    if request.method == 'POST':
        action = request.form['action']
        if action == 'ban':
            user_id = int(request.form['user_id'])
            user = User.query.get(user_id)
            user.banned = not user.banned  # Toggle
            db.session.commit()
            flash(f'User {user.username} {"banned" if user.banned else "unbanned"}', 'success')
        # ... (other actions same)
    return render_template('admin.html', users=users, transactions=transactions, chats=chats, logs=logs)

# Game routes same...

# Other routes same (chat, search, etc.)

if __name__ == '__main__':
    socketio.run(app, debug=True)
