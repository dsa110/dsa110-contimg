# Production Deployment Checklist - DSA-110 Continuum Imaging Pipeline

**Date:** 2025-11-11  
**Status:** Pre-Deployment  
**Purpose:** Complete checklist for deploying pipeline to production

---

## Pre-Deployment Verification

### Critical Safeguards Verification

- [x] Group ID collision prevention implemented
- [x] Total time span validation implemented
- [x] MS files stage validation implemented
- [x] Calibration table existence validation implemented
- [x] Image file existence validation implemented
- [x] Error recovery for failed publishes implemented
- [x] Database-level locking implemented
- [x] Enhanced path validation implemented

### Environment Setup

- [ ] Verify casa6 Python environment exists:
      `/opt/miniforge/envs/casa6/bin/python`
- [ ] Verify required directories exist:
  - [ ] `/stage/dsa110-contimg/` (SSD staging)
  - [ ] `/data/dsa110-contimg/products/` (HDD production)
  - [ ] `/data/dsa110-contimg/state/` (database storage)
  - [ ] `/data/incoming/` (UVH5 input)
- [ ] Verify directory permissions:
  - [ ] Staging directory writable
  - [ ] Products directory writable
  - [ ] State directory writable
  - [ ] Input directory readable
- [ ] Verify disk space:
  - [ ] Staging (SSD): Minimum 500 GB free
  - [ ] Products (HDD): Minimum 2 TB free
  - [ ] State (HDD): Minimum 10 GB free

### Database Setup

- [ ] Verify database files exist or will be created:
  - [ ] `/data/dsa110-contimg/state/products.sqlite3`
  - [ ] `/data/dsa110-contimg/state/ingest.sqlite3`
  - [ ] `/data/dsa110-contimg/state/cal_registry.sqlite3`
  - [ ] `/data/dsa110-contimg/state/data_registry.sqlite3`
- [ ] Verify database schema migrations will run automatically
- [ ] Verify database backups configured (if applicable)

### Configuration

- [ ] Review and set environment variables in `ops/systemd/contimg.env`:
  - [ ] `CONTIMG_API_PORT` (default: 8000)
  - [ ] `CONTIMG_INPUT_DIR` (default: `/data/incoming`)
  - [ ] `CONTIMG_OUTPUT_DIR` (default: `/stage/dsa110-contimg`)
  - [ ] `CONTIMG_STATE_DIR` (default: `/data/dsa110-contimg/state`)
  - [ ] `CONTIMG_PRODUCTS_DB` (default:
        `/data/dsa110-contimg/state/products.sqlite3`)
  - [ ] `CONTIMG_REGISTRY_DB` (default:
        `/data/dsa110-contimg/state/data_registry.sqlite3`)
- [ ] Verify CASA6 Python path:
      `CASA6_PYTHON_BIN=/opt/miniforge/envs/casa6/bin/python`
- [ ] Review pipeline configuration files (if any)

### Service Deployment

- [ ] **API Service:**
  - [ ] Copy systemd service file: `ops/systemd/contimg-api.service` →
        `/etc/systemd/system/`
  - [ ] Copy environment file: `ops/systemd/contimg.env` →
        `/data/dsa110-contimg/ops/systemd/`
  - [ ] Reload systemd: `sudo systemctl daemon-reload`
  - [ ] Enable service: `sudo systemctl enable contimg-api.service`
  - [ ] Start service: `sudo systemctl start contimg-api.service`
  - [ ] Verify status: `sudo systemctl status contimg-api.service`

- [ ] **Streaming Service (if enabled):**
  - [ ] Copy systemd service file: `ops/systemd/contimg-stream.service` →
        `/etc/systemd/system/`
  - [ ] Enable service: `sudo systemctl enable contimg-stream.service`
  - [ ] Start service: `sudo systemctl start contimg-stream.service`
  - [ ] Verify status: `sudo systemctl status contimg-stream.service`

- [ ] **Frontend (if separate):**
  - [ ] Build frontend: `cd frontend && npm run build`
  - [ ] Verify build output in `frontend/dist/`
  - [ ] Configure web server (Nginx/Apache) or use FastAPI static mount

### Health Checks

- [ ] **API Health:**
  - [ ] Check endpoint: `curl http://localhost:8000/api/status`
  - [ ] Verify response includes queue statistics
  - [ ] Check metrics: `curl http://localhost:8000/api/metrics/system`
  - [ ] Verify response includes CPU, memory, disk metrics

- [ ] **Database Health:**
  - [ ] Verify databases are accessible
  - [ ] Verify schema migrations completed
  - [ ] Check for any database errors in logs

- [ ] **Monitoring Endpoints:**
  - [ ] Check publish status:
        `curl http://localhost:8000/api/monitoring/publish/status`
  - [ ] Check failed publishes:
        `curl http://localhost:8000/api/monitoring/publish/failed`
  - [ ] Verify response includes metrics

### Logging Setup

- [ ] Verify log directories exist:
  - [ ] `/data/dsa110-contimg/state/logs/`
- [ ] Verify log rotation configured (if applicable)
- [ ] Test log writing:
  - [ ] Check API logs:
        `tail -f /data/dsa110-contimg/state/logs/contimg-api.out`
  - [ ] Check API errors:
        `tail -f /data/dsa110-contimg/state/logs/contimg-api.err`

### Monitoring Setup

- [ ] **Metrics Collection:**
  - [ ] Verify monitoring script exists: `scripts/monitor_publish_status.py`
  - [ ] Test monitoring script:
        `python scripts/monitor_publish_status.py --test`
  - [ ] Set up cron job for periodic monitoring (if desired)

- [ ] **Alerting (Optional):**
  - [ ] Configure alert thresholds:
    - [ ] Failed publishes > 5 in 1 hour
    - [ ] Mosaics stuck in staging > 24 hours
    - [ ] Publish success rate < 95%
  - [ ] Set up notification mechanism (email, Slack, etc.)

### Testing

- [ ] **End-to-End Test (Dry Run):**
  - [ ] Test group formation: Verify groups form correctly
  - [ ] Test mosaic creation: Verify mosaics create correctly
  - [ ] Test publish workflow: Verify auto-publish triggers
  - [ ] Test manual recovery: Verify manual publish works
  - [ ] Test monitoring: Verify metrics collection works

- [ ] **Load Test (Optional):**
  - [ ] Test with multiple concurrent groups
  - [ ] Test with rapid group creation
  - [ ] Verify no race conditions occur

### Documentation

- [ ] Review production readiness plan:
      `docs/reports/production_readiness_plan_2025-11-11.md`
- [ ] Review safeguards documentation:
      `docs/reports/safeguards_implemented_2025-11-10.md`
- [ ] Review enhancements documentation:
      `docs/reports/enhancements_implemented_2025-11-11.md`
- [ ] Document any custom configuration changes

---

## Deployment Steps

### Step 1: Pre-Deployment Verification

```bash
# Run pre-deployment checks
cd /data/dsa110-contimg
./scripts/validate_production_setup.sh
```

### Step 2: Deploy Services

```bash
# Option A: Using deployment script
cd /data/dsa110-contimg
./ops/deploy.sh --mode both

# Option B: Manual systemd deployment
sudo cp ops/systemd/contimg-api.service /etc/systemd/system/
sudo cp ops/systemd/contimg-stream.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable contimg-api.service contimg-stream.service
sudo systemctl start contimg-api.service contimg-stream.service
```

### Step 3: Verify Deployment

```bash
# Check service status
sudo systemctl status contimg-api.service
sudo systemctl status contimg-stream.service

# Check API health
curl http://localhost:8000/api/status
curl http://localhost:8000/api/metrics/system

# Check monitoring endpoints
curl http://localhost:8000/api/monitoring/publish/status
curl http://localhost:8000/api/monitoring/publish/failed
```

### Step 4: Start Monitoring

```bash
# Start monitoring script (optional)
python scripts/monitor_publish_status.py --daemon

# Or set up cron job
# Add to crontab: */5 * * * * /data/dsa110-contimg/scripts/run_casa_cmd.sh /opt/miniforge/envs/casa6/bin/python /data/dsa110-contimg/scripts/monitor_publish_status.py
```

---

## Post-Deployment Monitoring

### First 24 Hours

- [ ] Monitor service logs every hour
- [ ] Check publish success rate every 4 hours
- [ ] Verify no failed publishes accumulate
- [ ] Check system resources (CPU, memory, disk)

### First Week

- [ ] Review publish success rate daily
- [ ] Check for any failed publishes requiring manual intervention
- [ ] Verify monitoring alerts are working (if configured)
- [ ] Review system performance metrics

### Ongoing

- [ ] Weekly review of publish metrics
- [ ] Monthly review of system performance
- [ ] Quarterly review of safeguards effectiveness

---

## Rollback Plan

If issues occur after deployment:

1. **Stop Services:**

   ```bash
   sudo systemctl stop contimg-api.service
   sudo systemctl stop contimg-stream.service
   ```

2. **Review Logs:**

   ```bash
   tail -100 /data/dsa110-contimg/state/logs/contimg-api.err
   ```

3. **Fix Issues:**
   - Address any configuration issues
   - Fix any code bugs
   - Resolve any database issues

4. **Redeploy:**
   ```bash
   sudo systemctl start contimg-api.service
   sudo systemctl start contimg-stream.service
   ```

---

## Emergency Contacts

- **System Administrator:** [TBD]
- **Pipeline Developer:** [TBD]
- **On-Call Engineer:** [TBD]

---

## Related Documentation

- **Production Readiness Plan:**
  `docs/reports/production_readiness_plan_2025-11-11.md`
- **Safeguards Implemented:**
  `docs/reports/safeguards_implemented_2025-11-10.md`
- **Enhancements Implemented:**
  `docs/reports/enhancements_implemented_2025-11-11.md`
- **API Documentation:** `docs/reference/dashboard_backend_api.md`

---

**Status:** Ready for Production Deployment  
**Last Updated:** 2025-11-11
