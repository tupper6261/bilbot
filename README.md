# MapTap Daily Leaderboard Bot

## 1. Create the bot (Discord Developer Portal)
1. https://discord.com/developers/applications → **New Application**
2. **Bot** tab → **Reset Token** → copy it (this is `DISCORD_TOKEN`)
3. Same tab → turn on **Message Content Intent** (required to read scores)
4. **OAuth2 → URL Generator** → scope `bot`, permissions: *View Channel*, *Read Message History*, *Send Messages* → open the URL and add it to your server
5. In Discord, enable Developer Mode (Settings → Advanced), right-click the channel → **Copy Channel ID** (`CHANNEL_ID`)

## 2. Host it free on GitHub Actions
1. Create a **private** GitHub repo (public repos get scheduled workflows disabled after 60 days of inactivity) and push `bot.py` and `.github/workflows/leaderboard.yml`
2. Repo → **Settings → Secrets and variables → Actions** → add `DISCORD_TOKEN` and `CHANNEL_ID`
3. **Actions** tab → *Daily MapTap Leaderboard* → **Run workflow**. Manual runs default to dry run; tick **print_raw** to see every message the bot read and whether it matched.

## Test locally
```
pip install requests
DISCORD_TOKEN=... CHANNEL_ID=... DRY_RUN=1 PRINT_RAW=1 python bot.py
```
