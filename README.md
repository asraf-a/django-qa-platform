# Collaborative Q&A Platform

A Django-based collaborative Q&A platform where registered users can post questions, provide answers, leave comments, and vote on content.

## Tech Stack
- **Backend**: Python, Django
- **Database**: SQLite (development)
- **Frontend**: HTML5, Tailwind CSS, Alpine.js
- **Version Control**: Git

## Project Structure
```text
django-qa-platform/
├── .gitignore
├── README.md
├── requirements.txt
│
└── qa-platform/
    ├── manage.py
    ├── config/
    │   ├── __init__.py
    │   ├── settings.py
    │   ├── urls.py
    │   ├── asgi.py
    │   └── wsgi.py
    ├── app/
    │   ├── __init__.py
    │   ├── models/
    │   │   └── __init__.py
    │   ├── api/
    │   │   └── __init__.py
    │   ├── views/
    │   │   └── __init__.py
    │   ├── forms/
    │   │   └── __init__.py
    │   ├── templates/
    │   │   └── base.html
    │   ├── urls/
    │   │   └── __init__.py
    │   ├── admin.py
    │   ├── apps.py
    │   └── migrations/
    │       └── __init__.py
    └── static/
        ├── css/
        ├── js/
        └── images/
```

## Getting Started

### 1. Prerequisites
- Python 3.12+ installed
- Virtual environment created and activated

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Development Server
```bash
cd qa-platform
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` in your browser.
