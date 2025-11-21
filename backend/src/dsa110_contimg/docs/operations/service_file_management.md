# Managing Systemd Service Files

## The Permission Problem

Systemd service files in `/etc/systemd/system/` require **root permissions** to
edit. This is a security feature to prevent unauthorized modifications to system
services.

## Solutions

### Option 1: Edit Local Copy, Then Install (Recommended)

This is the **safest and recommended** approach:

1. **Edit the local copy** in your project directory:

   ```bash
   # Edit without sudo (no permission issues)
   nano /data/dsa110-contimg/src/dsa110_contimg/scripts/absurd/dsa110-absurd-worker@.service
   nano /data/dsa110-contimg/src/dsa110_contimg/scripts/absurd/dsa110-mosaic-daemon.service
   ```

2. **Install/update using the installation script:**

   ```bash
   cd /data/dsa110-contimg/src/dsa110_contimg
   sudo ./scripts/absurd/install_services.sh
   ```

   Or if services are already installed and you're updating:

   ```bash
   sudo ./scripts/absurd/update_services.sh
   ```

### Option 2: Edit System File Directly with Sudo

If you need to make quick changes:

```bash
# Edit the installed service file
sudo nano /etc/systemd/system/dsa110-absurd-worker@.service
sudo nano /etc/systemd/system/dsa110-mosaic-daemon.service

# After editing, reload systemd
sudo systemctl daemon-reload

# Restart services
sudo systemctl restart dsa110-mosaic-daemon
sudo systemctl restart dsa110-absurd-worker@{1..4}
```

### Option 3: Use systemctl edit (Systemd Override)

This creates an override file instead of modifying the original:

```bash
# Create an override file
sudo systemctl edit dsa110-mosaic-daemon.service

# This opens an editor where you can add/override specific settings
# Example override:
[Service]
Environment="ABSURD_DATABASE_URL=postgresql://newuser:newpass@localhost/dsa110_absurd"

# Save and exit - systemd automatically reloads
```

**Advantages:**

- Original service file remains intact
- Overrides are clearly separated
- Easier to track custom changes

**Location of overrides:**

```
/etc/systemd/system/dsa110-mosaic-daemon.service.d/override.conf
/etc/systemd/system/dsa110-absurd-worker@.service.d/override.conf
```

## Complete Workflow Example

### Scenario: Update Database Password

1. **Edit local service files:**

   ```bash
   cd /data/dsa110-contimg/src/dsa110_contimg/scripts/absurd

   # Update worker service
   sed -i 's/user:password/user:newpassword/g' dsa110-absurd-worker@.service

   # Update daemon service
   sed -i 's/user:password/user:newpassword/g' dsa110-mosaic-daemon.service
   ```

2. **Stop running services:**

   ```bash
   sudo systemctl stop dsa110-mosaic-daemon
   sudo systemctl stop 'dsa110-absurd-worker@*'
   ```

3. **Install updated services:**

   ```bash
   sudo ./install_services.sh
   ```

4. **Restart services:**

   ```bash
   sudo systemctl start dsa110-mosaic-daemon
   sudo systemctl start dsa110-absurd-worker@{1..4}
   ```

5. **Verify:**
   ```bash
   systemctl status dsa110-mosaic-daemon
   systemctl list-units 'dsa110-absurd-worker@*'
   ```

## Installation Scripts

### install_services.sh

**Purpose:** Initial installation of service files  
**Location:** `scripts/absurd/install_services.sh`  
**Usage:**

```bash
cd /data/dsa110-contimg/src/dsa110_contimg
sudo ./scripts/absurd/install_services.sh
```

**What it does:**

1. Checks for root permissions
2. Copies service files to `/etc/systemd/system/`
3. Sets correct permissions (644)
4. Reloads systemd daemon
5. Shows usage instructions

### update_services.sh

**Purpose:** Update existing service files  
**Location:** `scripts/absurd/update_services.sh`  
**Usage:**

```bash
cd /data/dsa110-contimg/src/dsa110_contimg
sudo ./scripts/absurd/update_services.sh
```

**What it does:**

1. Checks for root permissions
2. Detects running services
3. Prompts for confirmation
4. Stops services if running
5. Updates service files
6. Reloads systemd
7. Restarts services that were running
8. Shows status

## Common Tasks

### Add a New Environment Variable

**Edit local file:**

```bash
nano scripts/absurd/dsa110-mosaic-daemon.service
```

**Add line in `[Service]` section:**

```ini
Environment="MY_NEW_VAR=my_value"
```

**Apply:**

```bash
sudo ./scripts/absurd/update_services.sh
```

### Change Worker Count at Startup

**Edit local file:**

```bash
nano scripts/absurd/dsa110-absurd-worker@.service
```

**Modify `ExecStart` or add conditions**

**Apply:**

```bash
sudo ./scripts/absurd/update_services.sh
```

### Change Working Directory

**Edit local files to update `WorkingDirectory=`**

**Apply changes:**

```bash
sudo ./scripts/absurd/update_services.sh
```

## Troubleshooting

### "Permission denied" when editing

**Problem:** Trying to edit files in `/etc/systemd/system/` without sudo

**Solution:** Edit local copies in `scripts/absurd/` then run install script

### Changes not taking effect

**Problem:** Forgot to reload systemd

**Solution:**

```bash
sudo systemctl daemon-reload
sudo systemctl restart dsa110-mosaic-daemon dsa110-absurd-worker@*
```

### Service file syntax errors

**Problem:** Invalid systemd unit file syntax

**Diagnose:**

```bash
sudo systemd-analyze verify /etc/systemd/system/dsa110-mosaic-daemon.service
```

**Fix:** Correct syntax in local file, reinstall

### Can't find service after installation

**Problem:** Service not in systemd path

**Check:**

```bash
ls -la /etc/systemd/system/dsa110-*
systemctl list-unit-files | grep dsa110
```

## Best Practices

1. **Always edit local copies first** - Maintain version control
2. **Test changes in development** - Use test queues/databases
3. **Document changes** - Comment why you made modifications
4. **Backup before major changes**:
   ```bash
   sudo cp /etc/systemd/system/dsa110-mosaic-daemon.service \
           /etc/systemd/system/dsa110-mosaic-daemon.service.backup
   ```
5. **Use installation scripts** - Consistent, reproducible deployments
6. **Check logs after changes**:
   ```bash
   sudo journalctl -u dsa110-mosaic-daemon -n 50
   ```

## Quick Reference

```bash
# View current service file
systemctl cat dsa110-mosaic-daemon.service

# Check service status
systemctl status dsa110-mosaic-daemon

# View recent logs
sudo journalctl -u dsa110-mosaic-daemon -f

# Reload after manual edit
sudo systemctl daemon-reload

# Restart service
sudo systemctl restart dsa110-mosaic-daemon

# Enable auto-start
sudo systemctl enable dsa110-mosaic-daemon

# Disable auto-start
sudo systemctl disable dsa110-mosaic-daemon
```

## File Locations

| File                      | Location                                                                     |
| ------------------------- | ---------------------------------------------------------------------------- |
| **Source (Edit Here)**    | `/data/dsa110-contimg/src/dsa110_contimg/scripts/absurd/*.service`           |
| **Installed (Root Only)** | `/etc/systemd/system/*.service`                                              |
| **Overrides**             | `/etc/systemd/system/*.service.d/override.conf`                              |
| **Install Script**        | `/data/dsa110-contimg/src/dsa110_contimg/scripts/absurd/install_services.sh` |
| **Update Script**         | `/data/dsa110-contimg/src/dsa110_contimg/scripts/absurd/update_services.sh`  |

---

**Remember:** Never edit system service files directly in `/etc/systemd/system/`
for production systems. Always maintain source files in your project directory
and use installation scripts for consistency.
