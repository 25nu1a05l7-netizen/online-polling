# Create Polls, Gather Votes, Discover Consensus — Instantly

A complete Flask-based Online Polling / Voting System with quick anonymous polls, authenticated structured elections, audit logs, CSV export, live Chart.js dashboards, Bootstrap 5 UI, CSRF protection, and SQLite persistence.

## Setup

```bash
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5001`.

## Demo Accounts

Admin:

```text
email: admin@example.com
password: admin123
```

Regular user:

```text
email: student@example.com
password: student123
```

The application seeds one public quick poll and one public structured election on first run.

## Features

- User registration, login, logout, hashed passwords, Flask sessions, and role support.
- Authenticated poll/election creation with dynamic options, visibility, start time, expiry time, and unique links.
- Quick polls support anonymous voting with session/IP duplicate checks.
- Structured elections require login and enforce one vote per user.
- Vote audit logs capture poll, voter, timestamp, IP address, and action.
- Admin audit panel includes CSV export.
- Results page auto-refreshes via JavaScript Fetch API and renders bar and doughnut charts using Chart.js.
- Responsive Bootstrap 5 interface with dark/light theme, toast notifications, countdown timers, search, and pagination.

## Project Structure

```text
.
├── app.py
├── models.py
├── forms.py
├── requirements.txt
├── README.md
├── static/
│   ├── css/
│   ├── js/
│   └── images/
└── templates/
```
