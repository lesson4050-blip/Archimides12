#!/bin/bash
# Archimedes Backup Script v1.0
# Backs up database and workspace/data directories

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_PATH="$BACKUP_DIR/archimedes_backup_$TIMESTAMP"

mkdir -p "$BACKUP_PATH"

echo "Starting backup to $BACKUP_PATH..."

# 1. Backup Database (SQLite)
if [ -f "./data/archimedes.db" ]; then
    cp "./data/archimedes.db" "$BACKUP_PATH/"
    echo "✔ Database backed up"
else
    echo "✘ Database not found at ./data/archimedes.db"
fi

# 2. Backup Workspace
if [ -d "./workspace" ]; then
    tar -czf "$BACKUP_PATH/workspace.tar.gz" ./workspace
    echo "✔ Workspace backed up"
fi

# 3. Backup Skills & Artifacts
if [ -d "./data/skills" ]; then
    tar -czf "$BACKUP_PATH/skills.tar.gz" ./data/skills
fi
if [ -d "./data/artifacts" ]; then
    tar -czf "$BACKUP_PATH/artifacts.tar.gz" ./data/artifacts
fi

# Create summary
echo "Backup completed at $(date)" > "$BACKUP_PATH/summary.txt"
echo "Archimedes Version: 3.0.0" >> "$BACKUP_PATH/summary.txt"

# Compress everything
tar -czf "$BACKUP_PATH.tar.gz" -C "$BACKUP_DIR" "archimedes_backup_$TIMESTAMP"
rm -rf "$BACKUP_PATH"

echo "✔ ALL DONE: $BACKUP_PATH.tar.gz"

# Retention: keep only last 5 backups
ls -t $BACKUP_DIR/*.tar.gz | tail -n +6 | xargs rm -f 2>/dev/null
