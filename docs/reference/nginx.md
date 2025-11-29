# Nginx Configuration

The DSA-110 Continuum Imaging Pipeline uses Nginx as a reverse proxy to serve
the frontend and API.

## Configuration File

Location: `/etc/nginx/sites-available/dsa110-contimg`

## Architecture

```
                     ┌─────────────────────────────────────┐
                     │           Nginx (Port 80)          │
                     └─────────────────────────────────────┘
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            ▼                         ▼                         ▼
    ┌───────────────┐       ┌─────────────────┐       ┌─────────────────┐
    │   Frontend    │       │    /api/*       │       │    /metrics     │
    │  Static Files │       │   Proxy Pass    │       │ (localhost only)│
    │   (Vue.js)    │       │   Port 8000     │       │                 │
    └───────────────┘       └─────────────────┘       └─────────────────┘
```

## URL Routing

| Path        | Destination                          | Notes                       |
| ----------- | ------------------------------------ | --------------------------- |
| `/`         | `/data/dsa110-contimg/frontend/dist` | Vue.js SPA                  |
| `/api/*`    | `http://localhost:8000/api/*`        | FastAPI backend             |
| `/metrics`  | `http://localhost:8000/metrics`      | Prometheus (localhost only) |
| `/assets/*` | Static files with 1-year cache       | Immutable assets            |

## Features

### Gzip Compression

Enabled for text-based content types:

- `text/plain`
- `text/css`
- `application/json`
- `application/javascript`
- `text/xml`
- `application/xml`

### Security Headers

| Header                   | Value         | Purpose                    |
| ------------------------ | ------------- | -------------------------- |
| `X-Frame-Options`        | SAMEORIGIN    | Prevent clickjacking       |
| `X-Content-Type-Options` | nosniff       | Prevent MIME type sniffing |
| `X-XSS-Protection`       | 1; mode=block | XSS filter                 |

### Proxy Headers

Headers forwarded to the FastAPI backend:

- `Host`
- `X-Real-IP`
- `X-Forwarded-For`
- `X-Forwarded-Proto`

## Management

### Test Configuration

```bash
sudo nginx -t
```

### Reload Configuration

```bash
sudo systemctl reload nginx
```

### Check Status

```bash
sudo systemctl status nginx
```

### View Logs

```bash
# Access logs
sudo tail -f /var/log/nginx/access.log

# Error logs
sudo tail -f /var/log/nginx/error.log
```

## Customization

### Change Server Name

Edit the `server_name` directive:

```nginx
server_name dsa110.example.com;
```

### Enable HTTPS

Add SSL certificate configuration:

```nginx
server {
    listen 443 ssl;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    # ... rest of config
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    return 301 https://$host$request_uri;
}
```

### Allow Metrics from Prometheus Server

Update the `/metrics` location block:

```nginx
location /metrics {
    allow 127.0.0.1;
    allow ::1;
    allow 192.168.1.100;  # Prometheus server IP
    deny all;
    proxy_pass http://dsa110_api/metrics;
}
```

## Troubleshooting

### 502 Bad Gateway

The API server is not running:

```bash
sudo systemctl status dsa110-api.service
sudo systemctl start dsa110-api.service
```

### 403 Forbidden

Check file permissions:

```bash
ls -la /data/dsa110-contimg/frontend/dist
```

### Configuration Syntax Error

```bash
sudo nginx -t 2>&1
```
