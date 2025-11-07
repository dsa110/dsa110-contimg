# Troubleshooting

- CASA open errors → use direct-subband writer; ensure imaging columns
- .fuse_hidden files → clean after confirming no open FDs
- Stale groups → API reprocess, housekeeping utility, scheduler
- Performance → adjust workers, OMP/MKL threads, use fast scratch

## API Service

For detailed API restart and troubleshooting procedures, see:
- **[API Restart Guide](../operations/API_RESTART_GUIDE.md)** - Complete guide for restarting and troubleshooting the API service

Quick reference:
```bash
cd /data/dsa110-contimg/ops/docker
docker-compose restart api
```

