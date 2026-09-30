# AskCouple Telegram Bot

Telegram marketing + group-management bot for AskCouple.

## Included
- Admin-only marketing commands
- LIVE announcement preview and approval
- Real product-photo support (upload the real photo to Telegram with `/live ...` as its caption)
- Scheduled announcements
- Welcome message
- Basic suspicious/promotional link removal
- Singapore timezone
- `/id` command to obtain the admin Telegram user ID

## Commands

`/live 8:40 AM | Kinohimitsu | Join us for today's special LIVE!`

For a product image, upload the **real product image** to the Telegram group and use the `/live ...` command above as the photo caption.

`/schedule 2026-10-01 08:00 | Kinohimitsu | We are LIVE today at 8:40 AM!`

`/announce Your announcement`

`/id`

`/rules`

`/help`

## Important security
Never commit your BotFather token to GitHub. Add it only as the `BOT_TOKEN` environment variable in Render.

## Render
Create a Background Worker from this repository.

Environment variables:
- `BOT_TOKEN` = token supplied by BotFather
- `ADMIN_IDS` = your Telegram numeric user ID (get it by temporarily deploying, then sending `/id`)
- `TIMEZONE` = `Asia/Singapore`

Build command:
`pip install -r requirements.txt`

Start command:
`python bot.py`

## First launch
1. Deploy with `BOT_TOKEN`.
2. Send `/id` to the bot/group and copy your numeric user ID.
3. Add that number to Render as `ADMIN_IDS`.
4. Redeploy.
5. Test `/help`.
6. Test `/live 8:40 AM | Test Brand | Test announcement`.
