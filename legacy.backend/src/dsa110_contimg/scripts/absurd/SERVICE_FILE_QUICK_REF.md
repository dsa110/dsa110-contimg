# Service File Quick Reference

## The Problem

:cross_mark: **Can't edit files in `/etc/systemd/system/`** (requires root permissions)

## The Solution

:white_heavy_check_mark: **Edit LOCAL copies, then install with script**

---

## Quick Steps

### 1. Edit Local Files (No Sudo Needed)

```bash
cd /data/dsa110-contimg/src/dsa110_contimg/scripts/absurd
nano dsa110-absurd-worker@.service
nano dsa110-mosaic-daemon.service
```

### 2. Install Changes

```bash
cd /data/dsa110-contimg/src/dsa110_contimg
sudo ./scripts/absurd/install_services.sh
```

---

## File Locations

| Type                   | Location                             |
| ---------------------- | ------------------------------------ |
| **Edit Here** (Source) | `scripts/absurd/*.service`           |
| **Installed** (System) | `/etc/systemd/system/*.service`      |
| **Install Script**     | `scripts/absurd/install_services.sh` |

---

## Common Tasks

### Change Environment Variable

```bash
# Edit local file
nano scripts/absurd/dsa110-mosaic-daemon.service

# Add/modify in [Service] section:
Environment="VAR_NAME=value"

# Install
sudo ./scripts/absurd/install_services.sh
```

### Quick Override (Alternative Method)

```bash
# Creates override file automatically
sudo systemctl edit dsa110-mosaic-daemon.service

# Add your changes in the editor
[Service]
Environment="NEW_VAR=value"

# Save & exit - automatically reloads!
```

---

## After Editing

```bash
# Reload systemd
sudo systemctl daemon-reload

# Restart services
sudo systemctl restart dsa110-mosaic-daemon
sudo systemctl restart dsa110-absurd-worker@{1..4}

# Check status
systemctl status dsa110-mosaic-daemon
```

---

## Verification

```bash
# View installed service
systemctl cat dsa110-mosaic-daemon.service

# Check if installed
systemctl list-unit-files | grep dsa110

# View recent logs
sudo journalctl -u dsa110-mosaic-daemon -n 20
```

---

## Full Documentation

**See:** `docs/operations/service_file_management.md`

For complete guide including:

- 3 editing methods
- Troubleshooting
- Best practices
- Detailed examples
