# Control Panel Documentation Index

## 📖 Documentation Overview

This directory contains comprehensive documentation for the DSA-110 Control Panel, a web-based interface for manual calibration, apply, and imaging operations.

## 🚀 Quick Start

**New users start here:**
1. Read [`CONTROL_PANEL_QUICKSTART.md`](CONTROL_PANEL_QUICKSTART.md) - Step-by-step guide with examples
2. Use [`CONTROL_PANEL_CHEATSHEET.md`](CONTROL_PANEL_CHEATSHEET.md) - Quick reference card

## 📚 Complete Documentation

### User Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| [`CONTROL_PANEL_QUICKSTART.md`](CONTROL_PANEL_QUICKSTART.md) | Step-by-step user guide with workflow examples | Operators, Scientists |
| [`CONTROL_PANEL_CHEATSHEET.md`](CONTROL_PANEL_CHEATSHEET.md) | Quick reference card with commands and troubleshooting | All Users |
| [`CONTROL_PANEL_README.md`](CONTROL_PANEL_README.md) | Complete architecture and API documentation | Advanced Users, Developers |

### Technical Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| [`IMPLEMENTATION_SUMMARY.md`](IMPLEMENTATION_SUMMARY.md) | Technical implementation details and design decisions | Developers |
| [`PORT_MANAGEMENT.md`](PORT_MANAGEMENT.md) | Service management and port reservation guide | System Administrators |
| [`systemd/INSTALL.md`](systemd/INSTALL.md) | Systemd service installation instructions | System Administrators |

### Project Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| [`MEMORY.md`](MEMORY.md) | Project memory and lessons learned | All Contributors |

## 🎯 Documentation by Use Case

### "I want to run a calibration job"
→ [`CONTROL_PANEL_QUICKSTART.md`](CONTROL_PANEL_QUICKSTART.md) - See "Example Workflow: Full Calibration & Imaging"

### "I need to start/stop services"
→ [`CONTROL_PANEL_CHEATSHEET.md`](CONTROL_PANEL_CHEATSHEET.md) - See "🚀 Starting Services"

### "Port 8000 is already in use"
→ [`PORT_MANAGEMENT.md`](PORT_MANAGEMENT.md) - See "Manual Port Management"

### "I want to understand the architecture"
→ [`CONTROL_PANEL_README.md`](CONTROL_PANEL_README.md) - See "Architecture" section

### "I need to set up systemd services"
→ [`systemd/INSTALL.md`](systemd/INSTALL.md) - Complete installation guide

### "Something's not working"
→ [`CONTROL_PANEL_CHEATSHEET.md`](CONTROL_PANEL_CHEATSHEET.md) - See "🐛 Troubleshooting"

### "I want to modify the code"
→ [`IMPLEMENTATION_SUMMARY.md`](IMPLEMENTATION_SUMMARY.md) - Technical details and file structure

## 🗂️ File Structure

```
/data/dsa110-contimg/
├── CONTROL_PANEL_INDEX.md          # This file - documentation index
├── CONTROL_PANEL_README.md         # Complete architecture docs
├── CONTROL_PANEL_QUICKSTART.md     # User guide with examples
├── CONTROL_PANEL_CHEATSHEET.md     # Quick reference card
├── IMPLEMENTATION_SUMMARY.md       # Technical implementation details
├── PORT_MANAGEMENT.md              # Service management guide
├── MEMORY.md                        # Project memory
│
├── src/dsa110_contimg/
│   ├── database/
│   │   └── jobs.py                 # Job database module
│   └── api/
│       ├── routes.py               # API endpoints (7 new)
│       ├── models.py               # Pydantic models
│       └── job_runner.py           # Background job execution
│
├── frontend/src/
│   ├── pages/
│   │   └── ControlPage.tsx         # Control panel UI
│   ├── api/
│   │   ├── queries.ts              # React Query hooks
│   │   └── types.ts                # TypeScript types
│   ├── components/
│   │   └── Navigation.tsx          # Navigation (Control menu added)
│   └── App.tsx                     # Routing (Control route added)
│
├── scripts/
│   └── manage-services.sh          # Service management script
│
├── systemd/
│   ├── dsa110-api.service          # API systemd unit
│   ├── dsa110-dashboard.service    # Dashboard systemd unit
│   └── INSTALL.md                  # Installation instructions
│
└── docker-compose.yml              # Docker Compose configuration
```

## 🔗 Related Documentation

- **Calibration**: See `docs/calibration.md` (if exists) or `src/dsa110_contimg/calibration/`
- **Imaging**: See `docs/imaging.md` (if exists) or `src/dsa110_contimg/imaging/`
- **API**: See `src/dsa110_contimg/api/routes.py` for endpoint definitions
- **Database**: See `src/dsa110_contimg/database/` for schema definitions

## 📊 Feature Matrix

| Feature | Status | Documentation |
|---------|--------|---------------|
| Manual Calibration | ✅ Complete | [Quickstart](CONTROL_PANEL_QUICKSTART.md#step-1-calibrate-a-calibrator-ms) |
| Apply Calibration | ✅ Complete | [Quickstart](CONTROL_PANEL_QUICKSTART.md#step-2-apply-calibration-to-target-ms) |
| Manual Imaging | ✅ Complete | [Quickstart](CONTROL_PANEL_QUICKSTART.md#step-3-image-the-calibrated-ms) |
| Live Log Streaming | ✅ Complete | [README](CONTROL_PANEL_README.md#log-streaming-details) |
| Job Status Tracking | ✅ Complete | [README](CONTROL_PANEL_README.md#job-status) |
| Artifact Discovery | ✅ Complete | [README](CONTROL_PANEL_README.md#job-runner-behavior) |
| Service Management | ✅ Complete | [Port Management](PORT_MANAGEMENT.md) |
| Systemd Integration | ✅ Complete | [systemd/INSTALL.md](systemd/INSTALL.md) |
| Image Preview | 🔄 Future | [README](CONTROL_PANEL_README.md#future-enhancements) |
| Job Cancellation | 🔄 Future | [README](CONTROL_PANEL_README.md#future-enhancements) |
| Batch Jobs | 🔄 Future | [README](CONTROL_PANEL_README.md#future-enhancements) |

## 🆘 Getting Help

1. **Check the cheatsheet**: [`CONTROL_PANEL_CHEATSHEET.md`](CONTROL_PANEL_CHEATSHEET.md)
2. **Search MEMORY.md**: [`MEMORY.md`](MEMORY.md) - Contains solutions to common issues
3. **Check service logs**: `/var/log/dsa110/api.log`
4. **Test manually**: See [Quickstart Prerequisites](CONTROL_PANEL_QUICKSTART.md#prerequisites)

## 🔄 Version History

- **2025-10-27**: Initial release
  - Complete control panel implementation
  - Backend: 7 API endpoints, job database, background execution
  - Frontend: React UI with SSE log streaming
  - Service management: Script, systemd, Docker Compose
  - Documentation: 7 comprehensive guides

## 📝 Contributing

When modifying the control panel:
1. Update [`MEMORY.md`](MEMORY.md) with lessons learned
2. Update relevant documentation files
3. Test all three service management methods
4. Verify API endpoints with curl
5. Check frontend in browser

## 🎓 Learning Path

**Beginner** (Just want to use it):
1. [`CONTROL_PANEL_QUICKSTART.md`](CONTROL_PANEL_QUICKSTART.md)
2. [`CONTROL_PANEL_CHEATSHEET.md`](CONTROL_PANEL_CHEATSHEET.md)

**Intermediate** (Want to understand it):
1. [`CONTROL_PANEL_README.md`](CONTROL_PANEL_README.md)
2. [`PORT_MANAGEMENT.md`](PORT_MANAGEMENT.md)

**Advanced** (Want to modify it):
1. [`IMPLEMENTATION_SUMMARY.md`](IMPLEMENTATION_SUMMARY.md)
2. Source code in `src/dsa110_contimg/api/` and `frontend/src/`
3. [`MEMORY.md`](MEMORY.md) - Technical details section

---

**Quick Start Command**:
```bash
sudo fuser -k 8000/tcp && /data/dsa110-contimg/scripts/manage-services.sh start api
```

**Access Control Panel**: http://localhost:3000/control

