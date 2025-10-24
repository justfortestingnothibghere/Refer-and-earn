from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.utils import secure_filename
import os
import random
from datetime import datetime, timedelta
from models import db, User, Chat, Transaction, Referral, Notification, GameLog  # Import from models.py

app = Flask(__name__)
app.config['SECRET_KEY'] = 'c7ef14b68b6da888336a02d9d0e1b352'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'txt'}

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
socketio = SocketIO(app)

# Create DB tables
with app.app_context():
    db.create_all()
    # Create default admin if not exists
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@example.com', password_hash=generate_password_hash('adminpass'), is_admin=True, balance=999999, vip=True)
        db.session.add(admin)
        db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Home (dynamic)
@app.route('/')
def index():
    return render_template('index.html', user=current_user if current_user.is_authenticated else None)

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            # Daily reward check
            if user.last_login < datetime.now() - timedelta(days=1):
                user.balance += 50
                user.last_login = datetime.now()
                db.session.commit()
                flash('Daily login bonus: +50 coins!')
            return redirect(url_for('index'))
        flash('Invalid credentials')
    return render_template('login.html')

# Signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        phone = request.form.get('phone')
        ref_id = request.form.get('ref_id')  # From refer link
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            flash('User exists')
            return redirect(url_for('signup'))
        userid = f"USER_{random.randint(100000, 999999)}"
        user = User(username=username, email=email, password_hash=password, phone=phone, userid=userid, balance=100)  # Starter coins
        db.session.add(user)
        db.session.commit()
        if ref_id:
            referrer = User.query.filter_by(userid=ref_id).first()
            if referrer:
                referral = Referral(referrer_id=referrer.id, invited_userid=userid)
                db.session.add(referral)
                referrer.balance += 10  # Instant bonus
                db.session.commit()
                if len(referrer.referrals) == 10:
                    referrer.balance += 50
                elif len(referrer.referrals) == 25:
                    referrer.balance += 100
                db.session.commit()
        login_user(user)
        return redirect(url_for('index'))
    return render_template('signup.html')

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Profile
@app.route('/profile/<userid>')
@login_required
def profile(userid):
    user = User.query.filter_by(userid=userid).first_or_404()
    return render_template('profile.html', profile_user=user)

# Edit Profile
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        current_user.bio = request.form.get('bio')
        current_user.hide_phone = 'hide_phone' in request.form
        if 'dp' in request.files:
            file = request.files['dp']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                current_user.profile_dp = filename
        db.session.commit()
        flash('Profile updated')
    return render_template('settings.html')

# Search Users
@app.route('/search')
@login_required
def search():
    query = request.args.get('q')
    users = User.query.filter(User.userid.like(f'%{query}%')).all()
    return render_template('search.html', users=users)  # Assume search.html exists

# Chat
@app.route('/chat/<to_userid>')
@login_required
def chat(to_userid):
    to_user = User.query.filter_by(userid=to_userid).first_or_404()
    chats = Chat.query.filter(((Chat.from_userid == current_user.userid) & (Chat.to_userid == to_userid)) |
                              ((Chat.from_userid == to_userid) & (Chat.to_userid == current_user.userid))).order_by(Chat.timestamp).all()
    return render_template('chat.html', to_user=to_user, chats=chats)

# Upload Media for Chat/Profile
@app.route('/upload', methods=['POST'])
@login_required
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return jsonify({'url': f'/static/uploads/{filename}'})
    return jsonify({'error': 'Invalid file'}), 400

# Leaderboard
@app.route('/leaderboard')
def leaderboard():
    top_users = User.query.order_by(User.exp.desc()).limit(10).all()
    return render_template('leaderboard.html', top_users=top_users)

# Shop
@app.route('/shop', methods=['GET', 'POST'])
@login_required
def shop():
    if request.method == 'POST':
        item = request.form['item']
        if item == 'vip' and current_user.balance >= 500:
            current_user.vip = True
            current_user.balance -= 500
            db.session.commit()
            flash('VIP purchased!')
        # Add more items like avatars
    return render_template('shop.html')

# Games Routes
@app.route('/game/tictactoe')
@login_required
def game_tictactoe():
    return render_template('game_tictactoe.html')

@app.route('/game/spin')
@login_required
def game_spin():
    return render_template('game_spin.html')

@app.route('/game/rps')
@login_required
def game_rps():
    return render_template('game_rps.html')

@app.route('/game/coinflip')
@login_required
def game_coinflip():
    return render_template('game_coinflip.html')  # Similar JS

@app.route('/game/numberguess')
@login_required
def game_numberguess():
    return render_template('game_numberguess.html')  # JS for guessing

# Game API (for wins/losses)
@app.route('/game/win', methods=['POST'])
@login_required
def game_win():
    game_type = request.json['game']
    win = request.json['win']  # True/False from JS
    amount = random.randint(10, 50) if win else -20
    current_user.balance += amount
    current_user.exp += 10 if win else 5
    if current_user.exp >= current_user.level * 100:
        current_user.level += 1
        current_user.balance += 100  # Level up bonus
    log = GameLog(user_id=current_user.id, game_type=game_type, win=win, amount=amount)
    db.session.add(log)
    db.session.commit()
    return jsonify({'balance': current_user.balance, 'exp': current_user.exp, 'level': current_user.level})

# Transaction (Virtual - for demo, manual approve)
@app.route('/deposit', methods=['POST'])
@login_required
def deposit():
    amount = float(request.form['amount'])
    if 20 <= amount <= 1000:
        fee = amount * 0.1
        net = amount - fee
        if amount > 500:
            net += amount * 0.15  # Bonus
        trans = Transaction(user_id=current_user.id, type='deposit', amount=net, status='pending')
        db.session.add(trans)
        db.session.commit()
        flash('Deposit pending admin approval.')
    return redirect(url_for('profile', userid=current_user.userid))

@app.route('/withdraw', methods=['POST'])
@login_required
def withdraw():
    amount = float(request.form['amount'])
    if current_user.balance >= amount and Transaction.query.filter_by(user_id=current_user.id, type='withdraw').filter(Transaction.timestamp > datetime.now() - timedelta(days=1)).count() < 2:
        fee = amount * 0.2
        net = amount - fee
        trans = Transaction(user_id=current_user.id, type='withdraw', amount=net, status='pending')
        db.session.add(trans)
        db.session.commit()
        current_user.balance -= amount  # Lock until approve
        db.session.commit()
        flash('Withdraw pending.')
    return redirect(url_for('profile', userid=current_user.userid))

# Refer Link
@app.route('/refer')
def refer():
    ref_id = request.args.get('id')
    return redirect(url_for('signup', ref_id=ref_id))

# Secret Admin Panel
@app.route('/s/s/secret/1/000/admin/ap', methods=['GET', 'POST'])
@login_required
def admin():
    if not current_user.is_admin:
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
            user.banned = True
            db.session.commit()
        elif action == 'edit_balance':
            user_id = int(request.form['user_id'])
            new_balance = float(request.form['balance'])
            user = User.query.get(user_id)
            user.balance = new_balance
            db.session.commit()
        elif action == 'approve_trans':
            trans_id = int(request.form['trans_id'])
            trans = Transaction.query.get(trans_id)
            if trans.status == 'pending':
                if trans.type == 'deposit':
                    user = User.query.get(trans.user_id)
                    user.balance += trans.amount
                elif trans.type == 'withdraw':
                    # Simulate send
                    pass
                trans.status = 'approved'
                db.session.commit()
        elif action == 'delete_chat':
            chat_id = int(request.form['chat_id'])
            chat = Chat.query.get(chat_id)
            db.session.delete(chat)
            db.session.commit()
        elif action == 'set_win_rate':
            # Example: Global setting, store in DB if needed
            pass
        flash('Action performed')
    return render_template('admin.html', users=users, transactions=transactions, chats=chats, logs=logs)

# SocketIO for Chat
@socketio.on('join')
def on_join(data):
    room = sorted([data['from'], data['to']])
    room = '-'.join(room)
    join_room(room)

@socketio.on('send_message')
def handle_message(data):
    room = sorted([data['from'], data['to']])
    room = '-'.join(room)
    msg = Chat(from_userid=data['from'], to_userid=data['to'], message=data.get('text'), media_url=data.get('media'))
    # Moderation: Simple keyword ban
    banned_words = ['porn', 'illegal']
    if any(word in msg.message.lower() for word in banned_words):
        emit('message', {'msg': 'Message blocked'}, to=data['from'])
        # Ban user if repeated
        return
    db.session.add(msg)
    db.session.commit()
    emit('new_message', {'from': msg.from_userid, 'text': msg.message, 'media': msg.media_url}, room=room)

# Notifications (simple)
def send_notification(user_id, msg):
    notif = Notification(user_id=user_id, message=msg)
    db.session.add(notif)
    db.session.commit()

# Serve uploads
@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    socketio.run(app, debug=True)
