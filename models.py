from flask_login import UserMixin
from datetime import datetime
from app import db  # Import db from app.py


# ======================
# USER MODEL
# ======================
class User(UserMixin, db.Model):  # ✅ FIXED: must inherit from db.Model
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.String(20), unique=True)
    username = db.Column(db.String(50), unique=True)
    email = db.Column(db.String(100), unique=True)
    phone = db.Column(db.String(15))
    password_hash = db.Column(db.String(128))
    balance = db.Column(db.Float, default=0)
    exp = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
    vip = db.Column(db.Boolean, default=False)
    bio = db.Column(db.Text)
    profile_dp = db.Column(db.String(200))
    hide_phone = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    banned = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime, default=datetime.now)

    # Relationships
    referrals = db.relationship('Referral', backref='referrer', lazy='dynamic')
    transactions = db.relationship('Transaction', backref='user', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
    game_logs = db.relationship('GameLog', backref='user', lazy='dynamic')

    def __repr__(self):
        return f"<User {self.username}>"


# ======================
# CHAT MODEL
# ======================
class Chat(db.Model):
    __tablename__ = 'chat'

    id = db.Column(db.Integer, primary_key=True)
    from_userid = db.Column(db.String(20))
    to_userid = db.Column(db.String(20))
    message = db.Column(db.Text)
    media_url = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Chat from={self.from_userid} to={self.to_userid}>"


# ======================
# TRANSACTION MODEL
# ======================
class Transaction(db.Model):
    __tablename__ = 'transaction'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_transaction_user_id'))
    type = db.Column(db.String(10))
    amount = db.Column(db.Float)
    utr = db.Column(db.String(50))
    status = db.Column(db.String(20), default='pending')
    fee = db.Column(db.Float, default=0)
    timestamp = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Transaction user_id={self.user_id} amount={self.amount} status={self.status}>"


# ======================
# REFERRAL MODEL
# ======================
class Referral(db.Model):
    __tablename__ = 'referral'

    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_referral_referrer_id'))
    invited_userid = db.Column(db.String(20))

    def __repr__(self):
        return f"<Referral referrer_id={self.referrer_id} invited_userid={self.invited_userid}>"


# ======================
# NOTIFICATION MODEL
# ======================
class Notification(db.Model):
    __tablename__ = 'notification'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_notification_user_id'))
    message = db.Column(db.Text)
    read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Notification user_id={self.user_id} read={self.read}>"


# ======================
# GAME LOG MODEL
# ======================
class GameLog(db.Model):
    __tablename__ = 'game_log'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_game_log_user_id'))
    game_type = db.Column(db.String(50))
    win = db.Column(db.Boolean)
    amount = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f"<GameLog user_id={self.user_id} game_type={self.game_type} win={self.win}>"
