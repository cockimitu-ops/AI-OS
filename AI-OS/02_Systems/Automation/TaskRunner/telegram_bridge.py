import os
import sys
import time
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
import html
import re
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# 1. Konfiguration laden
load_dotenv("/home/nost/AI-OS/.env")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ALLOWED_USER = int(os.environ.get("TELEGRAM_ALLOWED_USER_ID", 0))

AIOS_DIR = os.environ.get("AIOS_WORKSPACE", "/home/nost/AI-OS/AI-OS/02_Systems/Automation/TaskRunner")
INBOX = os.path.join(AIOS_DIR, "tasks", "inbox")
LOGS = os.path.join(AIOS_DIR, "tasks", "logs")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agents
import memory
import proposals


def _split_agent_prefix(text):
    """A leading @alias selects an agent: "@research profile Acme".

    Unknown @words are left alone rather than treated as a failed agent
    selection - "@felix should I..." is a sentence, not a typo, and eating the
    first word of a real task would be worse than ignoring the prefix."""
    stripped = text.lstrip()
    if not stripped.startswith("@"):
        return None, text
    head, _, rest = stripped.partition(" ")
    resolved = agents.resolve(head)
    if not resolved:
        return None, text
    return resolved, rest.strip()

def _md_lite_to_telegram_html(text: str) -> str:
    """Converts fenced/inline code and **bold** into Telegram's HTML parse
    mode, so it actually renders. HTML mode only needs &, <, > escaped
    (versus MarkdownV2's ~18 special characters), so it never throws Telegram's
    "can't parse entities" 400 error against arbitrary/unpredictable model
    output the way Markdown mode does."""
    text = html.escape(text, quote=False)
    blocks = []

    def _stash_block(m):
        blocks.append(f"<pre><code>{m.group(2)}</code></pre>")
        return f"\x00BLOCK{len(blocks)-1}\x00"

    text = re.sub(r"```(\w*)\n?(.*?)```", _stash_block, text, flags=re.S)

    def _stash_inline(m):
        blocks.append(f"<code>{m.group(1)}</code>")
        return f"\x00BLOCK{len(blocks)-1}\x00"

    text = re.sub(r"`([^`\n]+)`", _stash_inline, text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)

    for i, block in enumerate(blocks):
        text = text.replace(f"\x00BLOCK{i}\x00", block)
    return text

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ALLOWED_USER:
        await update.message.reply_text(
            _md_lite_to_telegram_html("⛔ Zugriff verweigert: Unautorisierter Nutzer."),
            parse_mode=ParseMode.HTML,
        )
        return

    instruction = update.message.text.strip()
    if not instruction:
        return

    # Per-chat thread: the conversation you are already in is the unit of
    # memory, which is what makes a bare "now do the same for X" work.
    thread_id = f"tg_{update.effective_chat.id}"
    command = instruction.lower().lstrip("/").strip()

    if command in ("reset", "new", "forget", "clear"):
        existed = memory.reset(thread_id)
        await update.message.reply_text(
            _md_lite_to_telegram_html(
                "🧹 Memory gelöscht — nächste Nachricht startet frisch."
                if existed else "Nichts zu löschen, dieser Chat hat noch kein Memory."
            ),
            parse_mode=ParseMode.HTML,
        )
        return

    if command in ("memory", "context", "history"):
        await update.message.reply_text(
            _md_lite_to_telegram_html("🧠 **Memory**\n\n" + memory.summary(thread_id)),
            parse_mode=ParseMode.HTML,
        )
        return

    # The approval half of the propose/approve gate. This is the only place
    # a proposal becomes a task the worker will execute - the agents that
    # wrote them have no path into tasks/inbox/ at all (see proposals.py).
    if command == "proposals" or command == "review":
        await update.message.reply_text(
            _md_lite_to_telegram_html(proposals.format_review(proposals.load_review())),
            parse_mode=ParseMode.HTML,
        )
        return

    if command.startswith("approve"):
        selection = instruction.strip().lstrip("/")[len("approve"):]
        review = proposals.load_review()
        chosen, rejected, error = proposals.resolve(selection, review)
        if error:
            await update.message.reply_text(
                _md_lite_to_telegram_html(error), parse_mode=ParseMode.HTML)
            return

        # Approval branches on who can actually do the work. Queueing a
        # human-intervention item would hand the worker something it cannot
        # possibly do - "publish the Gumroad listing" - and a free model
        # given an impossible task tends to report success rather than
        # refuse. Those go on Felix's list instead.
        ai_items = [i for i in chosen if i.get("kind") == "ai"]
        human_items = [i for i in chosen if i.get("kind") != "ai"]

        for item in ai_items:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            name = f"task_approved_{stamp}.md"
            path = os.path.join(INBOX, name)
            body = (agents.directive(item["agent"])
                    if agents.resolve(item.get("agent", "")) else "")
            body += ("<!-- notify -->\n"
                     "(Approved by Felix from tonight's review.)\n\n"
                     f"{item['text']}\n")
            tmp = f"{path}.part"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(body)
            os.replace(tmp, path)

        proposals.add_todos(human_items)
        proposals.close_review(chosen, rejected)

        if not chosen:
            summary = f"Nothing approved — {len(rejected)} declined."
        else:
            parts = []
            if ai_items:
                parts.append(f"{len(ai_items)} queued for me")
            if human_items:
                parts.append(f"{len(human_items)} added to your list")
            summary = ("✅ " + ", ".join(parts)
                       + (f", {len(rejected)} declined." if rejected else "."))
            if human_items:
                summary += "\n\nSend `todo` to see your list."
        await update.message.reply_text(
            _md_lite_to_telegram_html(summary), parse_mode=ParseMode.HTML)
        return

    if command in ("todo", "todos", "list"):
        await update.message.reply_text(
            _md_lite_to_telegram_html(proposals.format_todos()),
            parse_mode=ParseMode.HTML)
        return

    if command.startswith("done"):
        done, error = proposals.complete_todo(instruction.strip().lstrip("/")[len("done"):])
        await update.message.reply_text(
            _md_lite_to_telegram_html(
                error or ("✅ Done: " + "; ".join(d.get("text", "") for d in done))),
            parse_mode=ParseMode.HTML)
        return

    if command in ("agents", "agent"):
        await update.message.reply_text(
            _md_lite_to_telegram_html(
                "**Agents** — put the alias first, e.g. `@research profile Acme Corp`\n\n"
                + agents.describe()
            ),
            parse_mode=ParseMode.HTML,
        )
        return

    agent, instruction = _split_agent_prefix(instruction)
    if not instruction:
        await update.message.reply_text(
            _md_lite_to_telegram_html("Agent erkannt, aber keine Aufgabe dahinter."),
            parse_mode=ParseMode.HTML,
        )
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    task_file = f"task_tg_{timestamp}.md"
    task_path = os.path.join(INBOX, task_file)
    log_path = os.path.join(LOGS, f"{task_file}.log")

    # In Inbox schreiben - atomar, siehe dispatch_task.py: der Worker pollt
    # tasks/inbox/*.md und darf keine halb geschriebene Datei sehen.
    body = (memory.directive(thread_id)
            + (agents.directive(agent) if agent else "")
            + instruction)
    tmp_path = f"{task_path}.part"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(body)
    os.replace(tmp_path, task_path)

    status_msg = await update.message.reply_text(
        _md_lite_to_telegram_html(
            f"⏳ Task eingereiht (`{task_file}`)"
            + (f" als **{agent.replace('_', ' ')}**" if agent else "")
            + ". Worker führt aus..."
        ),
        parse_mode=ParseMode.HTML,
    )

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

            await status_msg.edit_text(
                _md_lite_to_telegram_html(f"✅ **Ergebnis:**\n\n{result_text}"),
                parse_mode=ParseMode.HTML,
            )
            return
        await asyncio.sleep(2)

    await status_msg.edit_text(
        _md_lite_to_telegram_html("⚠️ **Timeout:** Der Worker hat innerhalb von 3 Minuten nicht geantwortet."),
        parse_mode=ParseMode.HTML,
    )

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
