# Deploy with systemd

- Edit `ops/systemd/contimg.env`
- Install units: copy to `/etc/systemd/system/`, daemon-reload
- Enable services: `contimg-stream.service`, `contimg-api.service`
- Logs: `journalctl -u contimg-stream -f`
