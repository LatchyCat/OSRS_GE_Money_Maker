# Runaway Background Sync Fix

## 🚨 IMMEDIATE SOLUTION

### Stop Runaway Process NOW
```bash
# Method 1: Use the emergency stop script
python stop_runaway_sync.py

# Method 2: Kill processes manually
pkill -f "python.*manage.py.*runserver"

# Method 3: Set environment variable
export DISABLE_AUTO_SYNC=true
```

### Restart Server Safely
```bash
# Use the safe restart script (RECOMMENDED)
python safe_restart.py

# OR manually with environment variable
export DISABLE_AUTO_SYNC=true
python manage.py runserver
```

## 🔧 WHAT WAS FIXED

### 1. Django Startup Control (`apps/system/apps.py`)
- Added `DISABLE_AUTO_SYNC` environment variable
- When set to `true`, prevents automatic sync on Django startup
- **This is the main fix that stops the runaway process**

### 2. Multi-Source Client Improvements (`services/multi_source_price_client.py`)
- Added connection limits (max 5 concurrent requests)
- Added rate limiting (2-second delay between batches)
- Added circuit breaker (stops after 10 consecutive failures)
- Enhanced cleanup with timeout protection
- Batch processing to prevent API overload

### 3. Sync Command Safety Limits (`apps/planning/management/commands/sync_items_and_prices.py`)
- Added `--max-requests` parameter (default: 500)
- Added `--request-delay` parameter (default: 2.0s)  
- Added `--dry-run` option for testing
- Added request counting and quota monitoring
- Added process timing and safety warnings

## 📋 MANUAL SYNC OPTIONS

### Safe Sync Commands
```bash
# Test what would be synced (no API calls)
python manage.py sync_items_and_prices --dry-run

# Sync only 50 items with safety limits
python manage.py sync_items_and_prices --limit 50 --max-requests 100

# Prices-only sync with rate limiting
python manage.py sync_items_and_prices --prices-only --max-requests 200 --request-delay 3.0

# Full sync with maximum safety
python manage.py sync_items_and_prices --max-requests 500 --request-delay 5.0
```

### Understanding the Limits
- `--max-requests 500`: Maximum 500 API calls total
- `--request-delay 3.0`: 3 second delay between API batches  
- `--limit 50`: Process only 50 items (good for testing)
- `--prices-only`: Skip item metadata, only update prices
- `--dry-run`: Show what would happen without making requests

## 🔍 MONITORING

### Check if Auto-Sync is Disabled
```bash
echo $DISABLE_AUTO_SYNC
# Should output: true
```

### Watch Server Logs
Look for these log messages:
- `🚫 Auto-sync disabled via DISABLE_AUTO_SYNC environment variable` (GOOD)
- `🚀 Django startup detected - initializing smart sync system...` (BAD - means auto-sync is enabled)

### Monitor API Requests
The enhanced sync command now shows:
- Request count: `📊 Request quota: 45/500 used`
- Batch processing: `📦 Processing batch 3/10 (5 items)`
- Safety warnings: `⚠️ Safety limits: max 500 requests, 2.0s delay`

## ⚡ RE-ENABLE AUTO-SYNC (WHEN SAFE)

### To re-enable auto-sync later:
```bash
# Remove the environment variable
unset DISABLE_AUTO_SYNC
# OR set it to false
export DISABLE_AUTO_SYNC=false

# Then restart Django
python manage.py runserver
```

## 🛡️ PREVENTION

### Best Practices Going Forward
1. **Always use the safe restart script** (`python safe_restart.py`)
2. **Test with dry-run first** (`--dry-run`) 
3. **Use small limits for testing** (`--limit 50`)
4. **Monitor request counts** (watch for quota warnings)
5. **Keep DISABLE_AUTO_SYNC=true during development**

### Environment Setup for Development
Add to your shell profile (`.bashrc`, `.zshrc`, etc.):
```bash
# Prevent OSRS sync runaway
export DISABLE_AUTO_SYNC=true
```

## 📊 WHAT CAUSED THE RUNAWAY

1. **Django Auto-Startup**: Every server restart triggered a full sync
2. **No Rate Limiting**: APIs were called as fast as possible
3. **No Request Limits**: Sync continued indefinitely
4. **Poor Connection Cleanup**: Connections stayed open causing loops
5. **No Circuit Breaker**: Failed requests were retried endlessly

All of these issues have been fixed with the new safety mechanisms.

## 🆘 EMERGENCY CONTACTS

If sync gets runaway again:
1. Run `python stop_runaway_sync.py`
2. Set `DISABLE_AUTO_SYNC=true` 
3. Kill Django processes: `pkill -f runserver`
4. Restart with `python safe_restart.py`

The system now has multiple layers of protection to prevent this from happening again.