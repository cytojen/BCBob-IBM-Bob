# BCB Audit Report

**Project:** test_app  
**Scanned:** 2026-05-16T16:28:03.147291Z  
**Files analyzed:** 3  
**LOC:** 130  


## Executive Summary

| Severity | Found | Fixed | Remaining |
| -------- | ----- | ----- | --------- |
| CRITICAL | 5 | 0 | 5 |
| HIGH | 1 | 0 | 1 |
| MEDIUM | 0 | 0 | 0 |
| LOW | 0 | 0 | 0 |


**Production readiness:** [X] NOT_READY



## Root Causes

### RC-001: Hardcoded Database Credentials

- **Severity:** CRITICAL
- **Confidence:** 0.50
- **Architectural cause:** Hardcoded database password in source code
- **Symptoms:** 1 findings across 1 files
- **Fix strategy:** Use environment variables
- **Files affected:**
  - `app.py`


### RC-002: SQL Injection

- **Severity:** CRITICAL
- **Confidence:** 0.50
- **Architectural cause:** SQL query built with string concatenation
- **Symptoms:** 1 findings across 1 files
- **Fix strategy:** Use parameterized queries
- **Files affected:**
  - `app.py`


### RC-003: Command Injection

- **Severity:** CRITICAL
- **Confidence:** 0.50
- **Architectural cause:** Command execution with user input
- **Symptoms:** 1 findings across 1 files
- **Fix strategy:** Use subprocess with shell=False
- **Files affected:**
  - `app.py`


### RC-004: Missing Auth Middleware (×2)

- **Severity:** CRITICAL
- **Confidence:** 0.50
- **Architectural cause:** API route without authentication
- **Symptoms:** 2 findings across 1 files
- **Fix strategy:** Add authentication middleware
- **Files affected:**
  - `app.py`


### RC-005: Debug Mode in Production

- **Severity:** HIGH
- **Confidence:** 0.50
- **Architectural cause:** Debug mode enabled
- **Symptoms:** 1 findings across 1 files
- **Fix strategy:** Set DEBUG=False in production
- **Files affected:**
  - `app.py`


## Detailed Findings

### CRITICAL Severity (5 findings)

#### [CRITICAL] Hardcoded Database Credentials — `app.py:17`

- **CWE:** CWE-798
- **Confidence:** 0.50
- **Description:** Hardcoded database password in source code

```

# VULNERABILITY: Hardcoded database credentials
DB_USER = "admin"
DB_PASSWORD = "password123"
DB_HOST = "localhost"

# VULNERABILITY: Hardcoded API key
```

**Fix:** Use environment variables



#### [CRITICAL] SQL Injection — `app.py:63`

- **CWE:** CWE-89
- **Confidence:** 0.50
- **Description:** SQL query built with string concatenation

```
    cursor = conn.cursor()
    
    # Another SQL injection
    query = "SELECT * FROM users WHERE name LIKE '%" + search_term + "%'"
    cursor.execute(query)
    
    results = cursor.fetchall()
```

**Fix:** Use parameterized queries



#### [CRITICAL] Command Injection — `app.py:97`

- **CWE:** CWE-78
- **Confidence:** 0.50
- **Description:** Command execution with user input

```
    filename = request.args.get('file', 'test.txt')
    
    # Command injection via os.system
    os.system(f"cat {filename}")
    
    return "Command executed"

```

**Fix:** Use subprocess with shell=False



#### [CRITICAL] Missing Auth Middleware — `app.py:102`

- **CWE:** CWE-306
- **Confidence:** 0.50
- **Description:** API route without authentication

```
    return "Command executed"


@app.route('/api/users', methods=['POST'])
def create_user():
    """VULNERABILITY: Mass assignment"""
    conn = get_db_connection()
```

**Fix:** Add authentication middleware



#### [CRITICAL] Missing Auth Middleware — `app.py:123`

- **CWE:** CWE-306
- **Confidence:** 0.50
- **Description:** API route without authentication

```
    return {"status": "created"}


@app.route('/api/admin')
def admin_panel():
    """VULNERABILITY: Missing authentication"""
    # No authentication check!
```

**Fix:** Add authentication middleware



### HIGH Severity (1 findings)

#### [HIGH] Debug Mode in Production — `app.py:185`

- **CWE:** CWE-489
- **Confidence:** 0.50
- **Description:** Debug mode enabled

```
    init_db()
    
    # VULNERABILITY: Debug mode in production
    app.run(debug=True, host='0.0.0.0')

```

**Fix:** Set DEBUG=False in production



## Needs Human Review

5 root causes require manual review:

- **RC-001:** Hardcoded Database Credentials (low confidence, critical severity)
- **RC-002:** SQL Injection (low confidence, critical severity)
- **RC-003:** Command Injection (low confidence, critical severity)
- **RC-004:** Missing Auth Middleware (×2) (low confidence, critical severity)
- **RC-005:** Debug Mode in Production (low confidence)

