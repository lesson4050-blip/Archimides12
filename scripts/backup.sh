#!/bin/bash
# Archimedes Backup Script v2.0 — with rotation and session memory
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP_DAYS="${KEEP_DAYS:-7}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="archimedes_${TIMESTAMP}"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

mkdir -p "$BACKUP_PATH"

echo "[$(date)] Starting backup: $BACKUP_NAME"

# 1. Backup SQLite databases (hot backup)
for db in data/*.db ./archemidas.db ./container.db; do
    if [ -f "$db" ]; then
        sqlite3 "$db" ".backup '${BACKUP_PATH}/$(basename $db)'" 2>/dev/null || cp "$db" "$BACKUP_PATH/"
        echo "  ✔ Backed up: $db"
    fi
done

# 2. Backup Workspace
if [ -d "./workspace" ]; then
    tar -czf "$BACKUP_PATH/workspace.tar.gz" ./workspace 2>/dev/null || true
    echo "  ✔ Workspace backed up"
fi

# 3. Backup Session Memory
if [ -d "data/session_memory" ]; then
    tar -czf "$BACKUP_PATH/session_memory.tar.gz" data/session_memory/ 2>/dev/null || true
    echo "  ✔ Session memory backed up"
fi

# 4. Backup Skills & Artifacts
if [ -d "data/skills" ]; then
    tar -czf "$BACKUP_PATH/skills.tar.gz" data/skills/ 2>/dev/null || true
    echo "  ✔ Skills backed up"
fi
if [ -d "data/artifacts" ]; then
    tar -czf "$BACKUP_PATH/artifacts.tar.gz" data/artifacts/ 2>/dev/null || true
    echo "  ✔ Artifacts backed up"
fi

# 5. Backup eval results
if [ -d "data/eval_results" ]; then
    tar -czf "$BACKUP_PATH/eval_results.tar.gz" data/eval_results/ 2>/dev/null || true
    echo "  ✔ Eval results backed up"
fi

# Create summary
echo "Backup completed at $(date)" > "$BACKUP_PATH/summary.txt"
echo "Archimedes Version: 3.0.0-godmode" >> "$BACKUP_PATH/summary.txt"
du -sh "$BACKUP_PATH"/* >> "$BACKUP_PATH/summary.txt" 2>/dev/null || true

# Compress everything
tar -czf "$BACKUP_PATH.tar.gz" -C "$BACKUP_DIR" "$BACKUP_NAME"
rm -rf "$BACKUP_PATH"

echo "  ✔ ALL DONE: $BACKUP_PATH.tar.gz"

# Rotation: keep only backups within KEEP_DAYS
find "$BACKUP_DIR" -name "archimedes_*.tar.gz" -mtime "+$KEEP_DAYS" -delete 2>/dev/null || true
# Also keep max 10 backups
ls -t $BACKUP_DIR/archimedes_*.tar.gz 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true

echo "[$(date)] Backup complete. Rotated backups older than $KEEP_DAYS days."
