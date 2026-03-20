# Telegram Gunpack Bot + Admin Panel

## Project Overview

A Telegram bot and web admin panel for distributing "gunpacks" (game modification asset packs). Users must subscribe to specific Telegram channels to unlock download links.

## Tech Stack

- **Language**: Python 3.12
- **Telegram Bot**: aiogram 3.x (async)
- **Web Framework**: Flask
- **Database**: SQLite via SQLAlchemy ORM
- **Auth**: Flask-Login + Flask-Bcrypt (admin panel), Telegram WebApp auth
- **Templates**: Jinja2 (dark theme)

## Project Structure

```
start.py              # Main entry point (starts bot + admin panel)
app.py                # Flask admin panel
bot.py                # Telegram bot logic (aiogram)
database.py           # SQLAlchemy models: User, Channel, Gunpack, Download
config.py             # Config loading from env vars
broadcast_handler.py  # Bulk message sending
channel_poster.py     # Channel post management
templates/            # Jinja2 HTML templates (dark theme)
static/               # CSS, images
```

## Environment Variables

Set via Replit Secrets/Env Vars:

| Variable         | Description                          | Required |
|------------------|--------------------------------------|----------|
| `BOT_TOKEN`      | Telegram Bot API token               | Yes (for bot) |
| `ADMIN_ID`       | Telegram user ID of the admin        | Yes      |
| `DB_PATH`        | SQLite database path (default: database.db) | No |
| `FLASK_SECRET_KEY` | Flask session secret key           | Yes      |
| `PORT`           | Web server port (default: 5000)      | No       |

## Running the Application

The workflow runs `python start.py` which:
1. Initializes the SQLite database and default channels
2. Starts the Telegram bot in a background thread (if `BOT_TOKEN` is set)
3. Starts the Flask admin panel on port 5000

## Admin Panel Access

- URL: `http://localhost:5000`
- Default login: `username=admin`, `password=admin123`
- Change this password after first login

## Deployment

Configured for VM deployment (always-running) since the Telegram bot requires a persistent process.
Run command: `python start.py`

## Notes

- The bot requires a valid `BOT_TOKEN` secret. Without it, only the admin panel starts.
- Default channels (@channel1, @channel2, @channel3) are created on first run.
- The admin panel supports dark theme throughout.
