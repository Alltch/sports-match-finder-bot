# Sports Match Finder Bot

Telegram bot that searches today's sports events through SofaScore and lets the user select a match.

## Supported sports

- Football
- Tennis
- Basketball
- Handball
- Ice hockey

## Local setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:

```env
BOT_TOKEN=your_real_token
OWNER_ID=0
```

Start the bot:

```bash
python bot.py
```

## Push to GitHub

```bash
git init
git add .
git commit -m "Initial sports match finder bot"
git branch -M main
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

The real `.env` file is intentionally excluded by `.gitignore`.

## Keep it running continuously with Railway

1. Create a new Railway project.
2. Select **Deploy from GitHub repo** and choose this repository.
3. In the Railway service, open **Variables** and add:

```text
BOT_TOKEN=your_real_token
OWNER_ID=0
```

4. Deploy the service.

The root `Dockerfile` starts `python bot.py`. The included `railway.json` sets the restart policy to `ALWAYS`.

## Updates

After changing code:

```bash
git add .
git commit -m "Describe the change"
git push
```
