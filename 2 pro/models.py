from datetime import datetime
from uuid import uuid4

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    polls = db.relationship("Poll", backref="creator", lazy=True)
    votes = db.relationship("Vote", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"


class Poll(db.Model):
    __tablename__ = "polls"

    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(36), default=lambda: str(uuid4()), unique=True, nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=True)
    mode = db.Column(db.String(20), nullable=False, default="quick")
    visibility = db.Column(db.String(20), nullable=False, default="public")
    start_time = db.Column(db.DateTime, nullable=False)
    expiry_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    options = db.relationship("PollOption", backref="poll", lazy=True, cascade="all, delete-orphan")
    votes = db.relationship("Vote", backref="poll", lazy=True, cascade="all, delete-orphan")
    audit_logs = db.relationship("VoteAuditLog", backref="poll", lazy=True, cascade="all, delete-orphan")

    @property
    def is_active(self):
        now = datetime.utcnow()
        return self.start_time <= now <= self.expiry_time

    @property
    def is_expired(self):
        return datetime.utcnow() > self.expiry_time

    @property
    def total_votes(self):
        return len(self.votes)


class PollOption(db.Model):
    __tablename__ = "poll_options"

    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey("polls.id"), nullable=False)
    option_text = db.Column(db.String(255), nullable=False)

    votes = db.relationship("Vote", backref="option", lazy=True, cascade="all, delete-orphan")


class Vote(db.Model):
    __tablename__ = "votes"

    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey("polls.id"), nullable=False, index=True)
    option_id = db.Column(db.Integer, db.ForeignKey("poll_options.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    session_token = db.Column(db.String(128), nullable=True, index=True)
    ip_address = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class VoteAuditLog(db.Model):
    __tablename__ = "vote_audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey("polls.id"), nullable=False, index=True)
    voter_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(80), nullable=False)
    ip_address = db.Column(db.String(64), nullable=True)
    details = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    voter = db.relationship("User")
