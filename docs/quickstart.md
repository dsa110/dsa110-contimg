# Quick Start

Pick one path: Docker Compose (easiest) or systemd (closer to the metal).

## Docker Compose

1) Copy and edit env
```
cp ops/docker/.env.example ops/docker/.env
# Edit absolute host paths: REPO_ROOT, CONTIMG_*; set UID/GID and CONTIMG_API_PORT
```
2) Build and start
```
make compose-build
make compose-up
make compose-logs SERVICE=stream
```
3) Verify
- Output MS under `${CONTIMG_OUTPUT_DIR}`
- Products DB `images` and `ms_index` in `${CONTIMG_PRODUCTS_DB}`
- API at `http://localhost:${CONTIMG_API_PORT}/api/status`

## systemd

1) Edit env and install units
```
vi ops/systemd/contimg.env
sudo mkdir -p /data/dsa110-contimg/state/logs
sudo cp ops/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now contimg-stream.service contimg-api.service
```
2) Verify
- `journalctl -u contimg-stream -f`
- API status at `/api/status`
