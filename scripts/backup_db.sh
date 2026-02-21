#!/bin/bash
# SQLite 数据库每日备份脚本
# 用法：bash scripts/backup_db.sh
# 建议通过 cron 每日执行：0 3 * * * /path/to/scripts/backup_db.sh
#
# 备份策略：
#   - 备份目录：data/backups/
#   - 文件名：app_YYYY-MM-DD.db
#   - 保留最近 30 天，自动清理旧备份

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DB_PATH="$PROJECT_DIR/data/app.db"
BACKUP_DIR="$PROJECT_DIR/data/backups"
DATE=$(date +%Y-%m-%d)
BACKUP_FILE="$BACKUP_DIR/app_${DATE}.db"
KEEP_DAYS=30

mkdir -p "$BACKUP_DIR"

if [ ! -f "$DB_PATH" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: 数据库文件不存在: $DB_PATH"
    exit 1
fi

# 使用 SQLite .backup 命令保证备份一致性（热备份，无需停服）
sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"

SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 备份成功: $BACKUP_FILE ($SIZE)"

# 清理超过 KEEP_DAYS 天的旧备份
find "$BACKUP_DIR" -name "app_*.db" -mtime +${KEEP_DAYS} -delete
REMAINING=$(find "$BACKUP_DIR" -name "app_*.db" | wc -l | tr -d ' ')
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 清理完成，当前保留 $REMAINING 个备份文件"
