import os
import time
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# 1. Konfiguration laden
load_dotenv("/home/nost/AI-OS/.env")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ALLOWED_USER = int(os.environ.get("TELEGRAM_ALLOWED_USER_ID", 0))

AIOS_DIR = os.environ.get("AIOS_WORKSPACE", "/home/nost/AI-OS/AI-OS/02_Systems/Automation/TaskRunner")
INBOX = os.path.join(AIOS_DIR, "tasks", "inbox")
LOGS = os.path.join(AIOS_DIR, "tasks", "logs")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ALLOWED_USER:
        await update.message.reply_text("⛔ Zugriff verweigert: Unautorisierter Nutzer.")
        return

    instruction = update.message.text.strip()
    if not instruction:
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    task_file = f"task_tg_{timestamp}.md"
    task_path = os.path.join(INBOX, task_file)
    log_path = os.path.join(LOGS, f"{task_file}.log")

    # In Inbox schreiben - atomar, siehe dispatch_task.py: der Worker pollt
    # tasks/inbox/*.md und darf keine halb geschriebene Datei sehen.
    tmp_path = f"{task_path}.part"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(instruction)
    os.replace(tmp_path, task_path)

    status_msg = await update.message.reply_text(f"⏳ Task eingereiht (`{task_file}`). Worker führt aus...")

    # Auf Worker-Ergebnis warten (max. 180s)
    timeout = 180
    start_time = time.time()

    while time.time() - start_time < timeout:
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as lf:
                result_text = lf.read().strip()

            if len(result_text) > 4000:
                truncated = result_text[:3950]
                if truncated.count("```") % 2 == 1:
                    truncated += "\n```"
                result_text = (
                    f"{truncated}\n\n... [Log gekürzt - vollständig in "
                    f"tasks/logs/{os.path.basename(log_path)}]"
                )

            await status_msg.edit_text(f"✅ **Ergebnis:**\n\n{result_text}")
            return
        await asyncio.sleep(2)

    await status_msg.edit_text("⚠️ **Timeout:** Der Worker hat innerhalb von 3 Minuten nicht geantwortet.")

def main():
    if not BOT_TOKEN or not ALLOWED_USER:
        print("FEHLER: TELEGRAM_BOT_TOKEN oder TELEGRAM_ALLOWED_USER_ID fehlen in .env!")
        return

    print("🤖 Telegram Bridge aktiv. Warte auf Nachrichten...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
