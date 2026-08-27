#!/usr/bin/env python3
"""Fully automated AI-OS backup: tar.gz the vault/scripts/configs, upload
to Google Drive via rclone, prune local archives older than the retention
window. Meant to run non-interactively (systemd timer or cron)."""
import os
import subprocess
import sys
import tarfile
import time

AIOS_DIR = "/home/nost/AI-OS"
NOTIFIER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "send_telegram_notification.py")
TASK_RUNNER_REL = "AI-OS/02_Systems/Automation/TaskRunner"
BACKUP_DIR = os.path.join(AIOS_DIR, TASK_RUNNER_REL, "backups")
RETENTION_DAYS = 7

# Set up once with: rclone config   (creates a remote named "gdrive")
RCLONE_REMOTE = "gdrive"
RCLONE_TARGET_FOLDER = "Server Backup"

EXCLUDE_DIR_NAMES = {".venv", "__pycache__", "node_modules"}
# Paths relative to AIOS_DIR. nextcloud/data and portainer/data are live
# container runtime volumes, not vault/config - excluded on purpose (also
# dwarfs the backup, and portainer/data has root-owned subdirs nost can't
# read anyway). The TaskRunner's own tasks/logs and backups/ are excluded too -
# logs are noisy/ephemeral, and backups/ holds this script's own prior output,
# which would otherwise balloon every new archive with all earlier ones.
EXCLUDE_RELATIVE_PATHS = {
    f"{TASK_RUNNER_REL}/tasks/logs",
    f"{TASK_RUNNER_REL}/backups",
    "server-stack/nextcloud/data",
    "server-stack/portainer/data",
    # Jellyfin's cache is regenerable and grows without bound once real media
    # is attached (transcodes especially) - nothing in it is worth restoring.
    # jellyfin/config IS kept, but note its jellyfin.db is a live SQLite file:
    # tarring it while the container is writing can capture an inconsistent
    # snapshot. Acceptable for a media server's metadata, not for anything
    # that would matter - don't extend this pattern to a real database.
    "server-stack/jellyfin/cache",
}


def _should_exclude(tarinfo):
    # tarinfo.name is "AI-OS/<relative path>" (arcname="AI-OS")
    rel = tarinfo.name.split("/", 1)[1] if "/" in tarinfo.name else ""
    parts = rel.split("/") if rel else []
    if any(part in EXCLUDE_DIR_NAMES for part in parts):
        return None
    if any(rel == p or rel.startswith(p + "/") for p in EXCLUDE_RELATIVE_PATHS):
        return None
    return tarinfo


def create_archive():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    archive_path = os.path.join(BACKUP_DIR, f"aios_backup_{timestamp}.tar.gz")

    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(AIOS_DIR, arcname="AI-OS", filter=_should_exclude)

    return archive_path


def upload_to_drive(archive_path):
    target = f"{RCLONE_REMOTE}:{RCLONE_TARGET_FOLDER}"
    result = subprocess.run(
        ["rclone", "copy", archive_path, target, "--stats-one-line"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def cleanup_old_archives():
    cutoff = time.time() - RETENTION_DAYS * 86400
    removed = []
    for name in os.listdir(BACKUP_DIR):
        path = os.path.join(BACKUP_DIR, name)
        if name.endswith(".tar.gz") and os.path.getmtime(path) < cutoff:
            os.remove(path)
            removed.append(name)
    return removed


def notify_failure(message):
    """This runs unattended from a systemd timer at 03:00 - a failure that only
    lands in the journal is a failure nobody sees. send_telegram_notification.py
    exists for exactly this and was never actually wired up to it."""
    try:
        subprocess.run([sys.executable, NOTIFIER, message], timeout=30, check=False)
    except Exception as e:  # never let the notifier itself mask the real failure
        print(f"Could not send failure notification: {e}", file=sys.stderr)


def main():
    archive_path = create_archive()
    size_mb = os.path.getsize(archive_path) / (1024 * 1024)

    uploaded, upload_log = upload_to_drive(archive_path)

    # Prune ONLY after a successful upload. Pruning unconditionally means a
    # silently broken remote (an unconfigured rclone, an expired token) deletes
    # local archives on schedule while nothing is landing in the cloud - after
    # RETENTION_DAYS there would be no backup in either place.
    removed = cleanup_old_archives() if uploaded else []

    print(f"Archive: {archive_path}")
    print(f"Size: {size_mb:.2f} MB")
    print(f"Uploaded to {RCLONE_REMOTE}:{RCLONE_TARGET_FOLDER}: {'OK' if uploaded else 'FAILED'}")
    if not uploaded:
        print(f"Upload output:\n{upload_log}")
        print(f"Keeping all local archives - pruning is skipped while uploads fail.")
        notify_failure(
            "AI-OS backup FAILED to upload.\n"
            f"Archive kept locally: {archive_path} ({size_mb:.2f} MB)\n"
            f"rclone: {upload_log[:500]}"
        )
    if removed:
        print(f"Removed local archives older than {RETENTION_DAYS}d: {', '.join(removed)}")

    sys.exit(0 if uploaded else 1)


if __name__ == "__main__":
    main()
