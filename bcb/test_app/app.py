"""
Sample vulnerable Flask application for testing BCB.
This app intentionally contains multiple security vulnerabilities.
"""

import os
import sqlite3
from flask import Flask, request, render_template_string, redirect

app = Flask(__name__)

# VULNERABILITY: Hardcoded secret key
app.secret_key = "secret123"

# VULNERABILITY: Hardcoded database credentials
DB_USER = "admin"
DB_PASSWORD = "password123"
DB_HOST = "localhost"

# VULNERABILITY: Hardcoded API key
API_KEY = "sk-1234567890abcdef"


def get_db_connection():
    """Get database connection."""
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def index():
    return "Welcome to the vulnerable app!"


@app.route('/user/<user_id>')
def get_user(user_id):
    """VULNERABILITY: SQL Injection via string concatenation"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # SQL injection vulnerability
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return f"User: {user['name']}"
    return "User not found"


@app.route('/search')
def search():
    """VULNERABILITY: SQL Injection in search"""
    search_term = request.args.get('q', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Another SQL injection
    query = "SELECT * FROM users WHERE name LIKE '%" + search_term + "%'"
    cursor.execute(query)
    
    results = cursor.fetchall()
    conn.close()
    
    return str(results)


@app.route('/render')
def render():
    """VULNERABILITY: XSS via render_template_string"""
    name = request.args.get('name', 'Guest')
    
    # XSS vulnerability - user input directly in template
    template = f"<h1>Hello {name}!</h1>"
    return render_template_string(template)


@app.route('/redirect')
def redirect_user():
    """VULNERABILITY: Open redirect"""
    url = request.args.get('url', '/')
    
    # Open redirect - no validation
    return redirect(url)


@app.route('/exec')
def execute_command():
    """VULNERABILITY: Command injection"""
    filename = request.args.get('file', 'test.txt')
    
    # Command injection via os.system
    os.system(f"cat {filename}")
    
    return "Command executed"


@app.route('/api/users', methods=['POST'])
def create_user():
    """VULNERABILITY: Mass assignment"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Mass assignment - accepts all fields from request
    data = request.json
    
    # This allows setting is_admin=True
    cursor.execute(
        "INSERT INTO users (name, email, is_admin) VALUES (?, ?, ?)",
        (data.get('name'), data.get('email'), data.get('is_admin', False))
    )
    
    conn.commit()
    conn.close()
    
    return {"status": "created"}


@app.route('/api/admin')
def admin_panel():
    """VULNERABILITY: Missing authentication"""
    # No authentication check!
    return {"admin": "panel", "users": ["user1", "user2"]}


@app.route('/upload', methods=['POST'])
def upload_file():
    """VULNERABILITY: Unrestricted file upload"""
    file = request.files.get('file')
    
    if file:
        # No validation of file type, size, or content
        file.save(f"uploads/{file.filename}")
        return "File uploaded"
    
    return "No file"


@app.route('/fetch')
def fetch_url():
    """VULNERABILITY: SSRF"""
    import requests
    
    url = request.args.get('url')
    
    # SSRF - fetches any URL without validation
    response = requests.get(url)
    
    return response.text


def init_db():
    """Initialize database."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            password TEXT,
            is_admin BOOLEAN DEFAULT 0
        )
    ''')
    
    # VULNERABILITY: Storing plain text passwords
    cursor.execute(
        "INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, ?)",
        ('admin', 'admin@example.com', 'admin123', 1)
    )
    
    conn.commit()
    conn.close()


if __name__ == '__main__':
    init_db()
    
    # VULNERABILITY: Debug mode in production
    app.run(debug=True, host='0.0.0.0')
