---
description: Add production-grade logging to the Spendly Flask app (app.py and database/db.py)
allowed-tools: Read, Write, Edit
---

## Task: Add Logging to Spendly

You are adding a logging system to this Flask expense tracker. Follow these steps exactly.

### Step 1 — Read current files first

Read `app.py` and `database/db.py` in full before making any changes.

### Step 2 — Add logging setup to `app.py`

At the top of `app.py`, after all existing imports, add:

```python
import logging
import os
from logging.handlers import RotatingFileHandler
```

After the line `app = Flask(__name__)`, add:

```python
# --- Logging Setup ---
os.makedirs("logs", exist_ok=True)
_log_formatter = logging.Formatter(
    "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
_file_handler = RotatingFileHandler(
    "logs/spendly.log", maxBytes=1_000_000, backupCount=3
)
_file_handler.setFormatter(_log_formatter)
_file_handler.setLevel(logging.INFO)
app.logger.addHandler(_file_handler)
app.logger.setLevel(logging.INFO)
```

### Step 3 — Add log statements to auth routes in `app.py`

In the `login` route:
- On successful login: `app.logger.info(f"LOGIN_SUCCESS | user_id={user['id']} | email={email}")`
- On failed login: `app.logger.warning(f"LOGIN_FAILED | email={email} | reason=invalid_credentials")`

In the `register` route:
- After user creation: `app.logger.info(f"REGISTER | user_id={new_user_id} | email={email}")`

In the `logout` route:
- Before clearing session: `app.logger.info(f"LOGOUT | user_id={session.get('user_id')}")`

### Step 4 — Add log statements to expense CRUD routes in `app.py`

In `add_expense`, after successful DB insert:
```python
app.logger.info(f"EXPENSE_ADD | user_id={session['user_id']} | amount={amount} | category={category} | date={date_str}")
```

In `edit_expense`, after successful DB update:
```python
app.logger.info(f"EXPENSE_EDIT | user_id={session['user_id']} | expense_id={expense_id} | amount={amount} | category={category}")
```

In `delete_expense`, after successful DB delete:
```python
app.logger.info(f"EXPENSE_DELETE | user_id={session['user_id']} | expense_id={expense_id}")
```

### Step 5 — Add ownership violation logging in `app.py`

Wherever a route checks `if expense['user_id'] != session['user_id']:`, add before the redirect:
```python
app.logger.warning(f"OWNERSHIP_VIOLATION | user_id={session['user_id']} | attempted_expense_id={expense_id}")
```

### Step 6 — Add module-level logger to `database/db.py`

After the existing imports in `db.py`, add:
```python
import logging
logger = logging.getLogger(__name__)
```

In each function that has a `try/finally` block, add an `except` clause that logs before re-raising:
```python
except Exception as e:
    logger.error(f"DB_ERROR | operation=<function_name> | error={e}")
    raise
```
Replace `<function_name>` with the actual function name: `create_user`, `create_expense`, `update_expense`, `delete_expense`.

### Step 7 — Update `.gitignore`

Check if `.gitignore` exists. If it does, append these lines if not already present: 
If `.gitignore` does not exist, create it with those two lines.
logs/
*.log

### Step 8 — Verify

After all edits:
1. Confirm `import logging` and `RotatingFileHandler` are present in `app.py`
2. Confirm `logs/` directory creation is in place
3. Confirm `logger = logging.getLogger(__name__)` is in `db.py`
4. Confirm `.gitignore` has `logs/` entry
5. Report a summary of every file changed and every log line added
