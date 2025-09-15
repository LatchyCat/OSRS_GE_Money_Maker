# 🚀 Quick Start Guide

The server failed because the PostgreSQL database doesn't exist yet. Here's how to fix it:

## Step 1: Set up the database

Run either of these scripts to create the database and run migrations:

**Option A: Python Script**
```bash
python setup_database.py
```

**Option B: Bash Script (Linux/macOS)**
```bash
./setup_database.sh
```

## Step 2: Start the server

After database setup is complete, start the server:

```bash
python start_server.py
# OR
./start_server.sh
```

## What the setup scripts do:

✅ **Check PostgreSQL**: Verify PostgreSQL is running  
🗄️ **Create Database**: Create the `osrs_tracker` database  
🔄 **Run Migrations**: Apply all Django migrations  
👤 **Create Superuser**: Optionally create admin account  

## Troubleshooting:

**If PostgreSQL isn't running:**
```bash
# macOS (with Homebrew)
brew services start postgresql

# Linux
sudo systemctl start postgresql

# Install PostgreSQL if needed
brew install postgresql  # macOS
```

**If database creation fails:**
- Make sure you can connect to PostgreSQL as the `postgres` user
- You might need to set a password: `createuser -s postgres`

## Alternative: Use SQLite for testing

If you want to quickly test without PostgreSQL, you can temporarily switch to SQLite:

1. Edit `backend/osrs_tracker/settings.py`
2. Replace the `DATABASES` section with:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```
3. Run migrations: `cd backend && python manage.py migrate`
4. Start server: `python ../start_server.py`

---

**The database setup only needs to be done once. After that, just use `start_server.py` to run the application!**