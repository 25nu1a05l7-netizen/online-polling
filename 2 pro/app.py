import csv
import io
import os
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin

from flask import Flask, Response, abort, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from werkzeug.exceptions import MethodNotAllowed, NotFound
from werkzeug.routing import RequestRedirect

from forms import LoginForm, PollForm, RegisterForm, VoteForm
from models import Poll, PollOption, User, Vote, VoteAuditLog, db


def build_poll_results(poll):
    rows = []
    total = 0
    for option in poll.options:
        votes = Vote.query.filter_by(option_id=option.id).count()
        total += votes
        rows.append({
            "id": option.id,
            "label": option.option_text,
            "votes": votes,
            "percentage": 0,
        })

    for row in rows:
        row["percentage"] = round((row["votes"] / total) * 100, 1) if total else 0

    participation = round((total / max(total + 10, 1)) * 100, 1)
    return rows, total, participation


def create_app():
    app = Flask(__name__)
    base_dir = os.path.abspath(os.path.dirname(__file__))
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(base_dir, 'database.db')}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=14)

    db.init_app(app)

    login_manager = LoginManager(app)
    login_manager.login_view = "login"
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.context_processor
    def inject_now():
        return {"now": datetime.utcnow()}

    @app.before_request
    def ensure_vote_session():
        session.permanent = True
        session.setdefault("anon_vote_token", secrets.token_urlsafe(32))

    @app.route("/")
    def index():
        q = request.args.get("q", "").strip()
        page = request.args.get("page", 1, type=int)
        query = Poll.query.filter_by(visibility="public").order_by(Poll.created_at.desc())
        if q:
            like = f"%{q}%"
            query = query.filter(Poll.title.ilike(like) | Poll.description.ilike(like))
        polls = query.paginate(page=page, per_page=6, error_out=False)
        return render_template("index.html", polls=polls, q=q)

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        form = RegisterForm()
        if form.validate_on_submit():
            if User.query.filter((User.username == form.username.data) | (User.email == form.email.data)).first():
                flash("Username or email is already registered.", "danger")
                return render_template("register.html", form=form)
            user = User(username=form.username.data, email=form.email.data, role="user")
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash("Account created. You can sign in now.", "success")
            return redirect(url_for("login"))
        return render_template("register.html", form=form)

    def is_safe_redirect(target):
        if not target:
            return False
        test_url = urlparse(urljoin(request.host_url, target))
        return test_url.scheme in ("http", "https") and test_url.netloc == urlparse(request.host_url).netloc

    def is_get_route(target):
        if not target:
            return False
        parsed = urlparse(target)
        try:
            app.url_map.bind_to_environ(request.environ).match(parsed.path, method="GET")
            return True
        except (MethodNotAllowed, NotFound, RequestRedirect):
            return False

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user and user.check_password(form.password.data):
                login_user(user)
                flash("Welcome back.", "success")
                next_page = request.args.get("next")
                if is_safe_redirect(next_page) and is_get_route(next_page):
                    return redirect(next_page)
                return redirect(url_for("dashboard"))
            flash("Invalid email or password.", "danger")
        return render_template("login.html", form=form)

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("You have been signed out.", "info")
        return redirect(url_for("index"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        q = request.args.get("q", "").strip()
        page = request.args.get("page", 1, type=int)
        query = Poll.query.filter_by(created_by=current_user.id).order_by(Poll.created_at.desc())
        if q:
            query = query.filter(Poll.title.ilike(f"%{q}%"))
        polls = query.paginate(page=page, per_page=8, error_out=False)
        total_votes = db.session.query(Vote).join(Poll).filter(Poll.created_by == current_user.id).count()
        return render_template("dashboard.html", polls=polls, q=q, total_votes=total_votes)

    @app.route("/polls/create", methods=["GET", "POST"])
    @login_required
    def create_poll():
        form = PollForm()
        if form.validate_on_submit():
            option_texts = [opt.strip() for opt in request.form.getlist("options[]") if opt.strip()]
            if len(option_texts) < 2:
                flash("Add at least two options.", "danger")
                return render_template("create_poll.html", form=form)
            if form.expiry_time.data <= form.start_time.data:
                flash("Expiry time must be after start time.", "danger")
                return render_template("create_poll.html", form=form)
            poll = Poll(
                title=form.title.data,
                description=form.description.data,
                mode=form.mode.data,
                visibility=form.visibility.data,
                start_time=form.start_time.data,
                expiry_time=form.expiry_time.data,
                created_by=current_user.id,
            )
            db.session.add(poll)
            db.session.flush()
            for text in option_texts:
                db.session.add(PollOption(poll_id=poll.id, option_text=text))
            db.session.commit()
            flash("Poll created. Share the link to start collecting votes.", "success")
            return redirect(url_for("poll_details", public_id=poll.public_id))
        return render_template("create_poll.html", form=form)

    @app.route("/polls/<public_id>/delete", methods=["POST"])
    @login_required
    def delete_poll(public_id):
        poll = Poll.query.filter_by(public_id=public_id, created_by=current_user.id).first_or_404()
        db.session.delete(poll)
        db.session.commit()
        flash("Poll deleted.", "success")
        return redirect(url_for("dashboard"))

    @app.route("/poll/<public_id>")
    @app.route("/polls/<public_id>")
    def poll_details(public_id):
        poll = Poll.query.filter_by(public_id=public_id).first_or_404()
        if poll.visibility == "private" and (not current_user.is_authenticated or current_user.id != poll.created_by):
            abort(404)
        return render_template("poll_details.html", poll=poll)

    @app.route("/poll/<public_id>/vote", methods=["GET", "POST"])
    @app.route("/polls/<public_id>/vote", methods=["GET", "POST"])
    def vote(public_id):
        poll = Poll.query.filter_by(public_id=public_id).first_or_404()
        if poll.mode == "election" and not current_user.is_authenticated:
            flash("Structured elections require login before voting.", "warning")
            return redirect(url_for("login", next=request.path))
        form = VoteForm()
        already_voted = has_voted(poll)
        if form.validate_on_submit():
            if not poll.is_active:
                flash("Voting is closed for this poll.", "danger")
                return redirect(url_for("poll_details", public_id=poll.public_id))
            if already_voted:
                flash("Your vote has already been recorded.", "warning")
                return redirect(url_for("results", public_id=poll.public_id))
            option = PollOption.query.filter_by(id=form.option_id.data, poll_id=poll.id).first()
            if not option:
                flash("Please choose a valid option.", "danger")
                return render_template("vote.html", poll=poll, form=form, already_voted=already_voted)
            vote_record = Vote(
                poll_id=poll.id,
                option_id=option.id,
                user_id=current_user.id if current_user.is_authenticated else None,
                session_token=session.get("anon_vote_token"),
                ip_address=request.remote_addr,
            )
            audit = VoteAuditLog(
                poll_id=poll.id,
                voter_id=current_user.id if current_user.is_authenticated else None,
                action="vote_cast",
                ip_address=request.remote_addr,
                details=f"Vote recorded for option #{option.id}",
            )
            db.session.add_all([vote_record, audit])
            db.session.commit()
            flash("Vote recorded successfully.", "success")
            return redirect(url_for("results", public_id=poll.public_id))
        return render_template("vote.html", poll=poll, form=form, already_voted=already_voted)

    @app.route("/poll/<public_id>/results")
    @app.route("/polls/<public_id>/results")
    def results(public_id):
        poll = Poll.query.filter_by(public_id=public_id).first_or_404()
        result_rows, total, participation = build_poll_results(poll)
        return render_template(
            "results.html",
            poll=poll,
            result_rows=result_rows,
            total=total,
            participation=participation,
        )

    @app.route("/api/poll/<public_id>/results")
    @app.route("/api/polls/<public_id>/results")
    def poll_results_api(public_id):
        poll = Poll.query.filter_by(public_id=public_id).first_or_404()
        result_rows, total, participation = build_poll_results(poll)
        return jsonify({
            "title": poll.title,
            "labels": [row["label"] for row in result_rows],
            "values": [row["votes"] for row in result_rows],
            "results": result_rows,
            "total": total,
            "participation": participation,
            "active": poll.is_active,
            "expires_at": poll.expiry_time.isoformat() + "Z",
        })

    @app.route("/admin")
    @login_required
    def admin():
        require_admin()
        page = request.args.get("page", 1, type=int)
        logs = VoteAuditLog.query.order_by(VoteAuditLog.timestamp.desc()).paginate(page=page, per_page=20, error_out=False)
        return render_template("admin.html", logs=logs)

    @app.route("/admin/export")
    @login_required
    def export_audit_csv():
        require_admin()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "poll_id", "poll_title", "voter_id", "action", "ip_address", "details", "timestamp"])
        for log in VoteAuditLog.query.order_by(VoteAuditLog.timestamp.desc()).all():
            writer.writerow([log.id, log.poll_id, log.poll.title, log.voter_id or "anonymous", log.action, log.ip_address, log.details, log.timestamp.isoformat()])
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=vote_audit_logs.csv"},
        )

    def require_admin():
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)

    def has_voted(poll):
        if poll.mode == "quick":
            return False  # Allow multiple votes in quick polls
        if current_user.is_authenticated:
            if Vote.query.filter_by(poll_id=poll.id, user_id=current_user.id).first():
                return True
        token = session.get("anon_vote_token")
        if token:
            if Vote.query.filter_by(poll_id=poll.id, session_token=token).first():
                return True
        if Vote.query.filter_by(poll_id=poll.id, ip_address=request.remote_addr).first():
            return True
        return False

    @app.cli.command("init-db")
    def init_db_command():
        init_db(app)
        print("Database initialized with sample data.")

    with app.app_context():
        init_db(app)

    return app


def init_db(app):
    db.create_all()
    if User.query.first():
        return
    admin = User(username="admin", email="admin@example.com", role="admin")
    admin.set_password("admin123")
    user = User(username="student", email="student@example.com", role="user")
    user.set_password("student123")
    db.session.add_all([admin, user])
    db.session.flush()

    poll = Poll(
        title="Best campus tech event format?",
        description="Help the organizing committee decide what students prefer this semester.",
        mode="quick",
        visibility="public",
        start_time=datetime.utcnow() - timedelta(hours=1),
        expiry_time=datetime.utcnow() + timedelta(days=5),
        created_by=admin.id,
    )
    election = Poll(
        title="Class Representative Election",
        description="A structured election demo with authenticated one-vote-per-user enforcement.",
        mode="election",
        visibility="public",
        start_time=datetime.utcnow() - timedelta(hours=1),
        expiry_time=datetime.utcnow() + timedelta(days=3),
        created_by=admin.id,
    )
    db.session.add_all([poll, election])
    db.session.flush()
    for text in ["Hackathon", "Paper presentation", "Project expo", "Tech quiz"]:
        db.session.add(PollOption(poll_id=poll.id, option_text=text))
    for text in ["Aarav Mehta", "Diya Sharma", "Kabir Rao"]:
        db.session.add(PollOption(poll_id=election.id, option_text=text))
    db.session.commit()


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5002)
