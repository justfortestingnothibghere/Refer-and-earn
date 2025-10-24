from flask_login import UserMixin
from datetime import datetime
from app import db  # Import db from app.py

# Define User first to ensure table exists for foreign keys
class User(UserMixin):
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
    referrals = db.relationship('Referral', backref='referrer')

class Chat(db.Model):
    __tablename__ = 'chat'
    id = db.Column(db.Integer, primary_key=True)
    from_userid = db.Column(db.String(20))
    to_userid = db.Column(db.String(20))
    message = db.Column(db.Text)
    media_url = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.now)

class Transaction(db.Model):
    __tablename__ = 'transaction'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Reference 'user' table
    type = db.Column(db.String(10))
    amount = db.Column(db.Float)
    utr = db.Column(db.String(50))
    status = db.Column(db.String(20), default='pending')
    fee = db.Column(db.Float, default=0)
    timestamp = db.Column(db.DateTime, default=datetime.now)

class Referral(db.Model):
    __tablename__ = 'referral'
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Reference 'user' table
    invited_userid = db.Column(db.String(20))

class Notification(db.Model):
    __tablename__ = 'notification'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Reference 'user' table
    message = db.Column(db.Text)
    read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)

class GameLog(db.Model):
    __tablename__ = 'game_log'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Reference 'user' table
    game_type = db.Column(db.String(50))
    win = db.Column(db.Boolean)
    amount = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.now)
