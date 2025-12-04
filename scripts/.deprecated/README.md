# Deprecated Scripts

These scripts have been replaced by ABSURD scheduled tasks for unified monitoring,
retry logic, and task history tracking.

## Moved Scripts

| Script                      | Replacement                    | ABSURD Schedule                                   |
| --------------------------- | ------------------------------ | ------------------------------------------------- |
| `backup-cron.sh`            | `backup-database` task         | `hourly_database_backup`, `daily_database_backup` |
| `install-cron-jobs.sh`      | Auto-registered on API startup | N/A                                               |
| `storage-reconciliation.sh` | `storage-reconciliation` task  | `daily_storage_reconciliation`                    |

## How to Use the New System

### View Schedules

```bash
curl http://localhost:8000/absurd/schedules | jq .
```

### Trigger Manual Backup

```bash
curl -X POST http://localhost:8000/absurd/schedules/hourly_database_backup/trigger
```

### View Task History

```bash
curl "http://localhost:8000/absurd/tasks?task_name=backup-database&limit=5" | jq .
```

## Emergency Use

These scripts are retained for emergencies when the API is down.
They can be run directly but will NOT integrate with ABSURD monitoring.

```bash
# Emergency database backup (no ABSURD tracking)
./backup-cron.sh hourly

# Emergency storage check (no ABSURD tracking)
./storage-reconciliation.sh
```

## See Also

- `backend/src/dsa110_contimg/absurd/maintenance.py` - Task implementations
- `docs/operations/RUNBOOK.md` - Operations procedures
