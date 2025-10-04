#!/bin/bash
# /data/dsa110-contimg/pipeline/scripts/backup_database.sh

DATE=$(date +%Y-%m-%d)
DB_FILE="/data/dsa110-contimg/database/ese_monitoring.db"
BACKUP_DIR="/data/dsa110-contimg/database/backups"

# Create compressed backup
sqlite3 $DB_FILE ".backup /tmp/ese_backup_temp.db"
gzip -c /tmp/ese_backup_temp.db > $BACKUP_DIR/ese_monitoring_$DATE.db.gz
rm /tmp/ese_backup_temp.db

# Keep only last 30 days of daily backups
find $BACKUP_DIR -name "ese_monitoring_*.db.gz" -mtime +30 -delete

# Weekly backup to offsite storage (keep last 12 weeks)
if [ $(date +%u) -eq 7 ]; then
    cp $BACKUP_DIR/ese_monitoring_$DATE.db.gz /backup/offsite/weekly/
    find /backup/offsite/weekly/ -name "*.db.gz" -mtime +84 -delete
fi

echo "Database backup completed: $DATE"