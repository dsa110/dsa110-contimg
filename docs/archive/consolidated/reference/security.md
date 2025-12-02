# DSA-110 API Security

## Overview

The DSA-110 API uses IP-based access control to restrict which clients can
access the API endpoints. This provides a simple security layer suitable for
internal observatory networks.

## How It Works

Every API request (except `/api/health`) is checked against a list of allowed IP
addresses and network ranges. Requests from unauthorized IPs receive a
`403 Forbidden` response.

## Default Allowed Networks

By default, the following are allowed:

| Network          | Description               |
| ---------------- | ------------------------- |
| `127.0.0.1`      | Localhost (IPv4)          |
| `::1`            | Localhost (IPv6)          |
| `10.0.0.0/8`     | Private network (Class A) |
| `172.16.0.0/12`  | Private network (Class B) |
| `192.168.0.0/16` | Private network (Class C) |

This means any machine on your local network can access the API, but external
internet requests are blocked.

## Customizing Allowed IPs

To allow additional IP addresses or networks, set the `DSA110_ALLOWED_IPS`
environment variable with a comma-separated list:

### Option 1: Shell Environment

```bash
# Allow specific external IP
export DSA110_ALLOWED_IPS="127.0.0.1,10.0.0.0/8,203.0.113.50"

# Start the API
python -m uvicorn dsa110_contimg.api.app:app --host 0.0.0.0 --port 8000
```

### Option 2: Systemd Service (Recommended for Production)

Edit the systemd service:

```bash
sudo systemctl edit dsa110-api.service
```

Add the following:

```ini
[Service]
Environment="DSA110_ALLOWED_IPS=127.0.0.1,10.0.0.0/8,192.168.0.0/16,203.0.113.50"
```

Then reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart dsa110-api.service
```

### Option 3: Environment File

Create `/etc/dsa110-api.env`:

```bash
DSA110_ALLOWED_IPS=127.0.0.1,10.0.0.0/8,192.168.0.0/16,203.0.113.50
```

Update the systemd service to use it:

```bash
sudo systemctl edit dsa110-api.service
```

```ini
[Service]
EnvironmentFile=/etc/dsa110-api.env
```

## IP Format Examples

| Format           | Description                                 |
| ---------------- | ------------------------------------------- |
| `192.168.1.100`  | Single IP address                           |
| `192.168.1.0/24` | Entire /24 subnet (192.168.1.0-255)         |
| `10.0.0.0/8`     | Class A network (10.0.0.0 - 10.255.255.255) |
| `2001:db8::1`    | IPv6 address                                |
| `2001:db8::/32`  | IPv6 network                                |

## Health Check Exception

The `/api/health` endpoint is **always accessible** regardless of IP
restrictions. This allows external monitoring tools to check API availability
without being whitelisted.

```bash
# Always works from any IP
curl http://your-server:8000/api/health
```

## Blocked Request Response

When a request is blocked, the client receives:

```json
{
  "code": "FORBIDDEN",
  "message": "Access denied from 1.2.3.4",
  "hint": "Contact administrator to whitelist your IP"
}
```

HTTP Status: `403 Forbidden`

## Proxy Considerations

If your API is behind a reverse proxy (nginx, Apache, etc.), the middleware
checks the `X-Forwarded-For` header first, then falls back to the direct client
IP.

**Important:** Ensure your proxy is configured to set `X-Forwarded-For`
correctly:

```nginx
# Nginx configuration
location /api/ {
    proxy_pass http://localhost:8000/api/;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header Host $host;
}
```

## Disabling IP Restrictions

To allow all IPs (not recommended for production):

```bash
export DSA110_ALLOWED_IPS="0.0.0.0/0"
```

This effectively disables the IP filter by allowing all IPv4 addresses.

## Troubleshooting

### Check Your IP

```bash
# From the client machine
curl -s http://your-server:8000/api/health
# If you get 403, the response shows your IP
```

### Verify Current Configuration

```bash
# Check what IPs are configured
grep DSA110_ALLOWED_IPS /etc/systemd/system/dsa110-api.service.d/*.conf
```

### Test from Specific IP

```bash
# Use curl with explicit source IP (if you have multiple interfaces)
curl --interface eth0 http://your-server:8000/api/images
```

## Alternative: API Key Authentication

For scenarios requiring per-client authentication (rather than per-IP), API key
authentication can be added. This is useful when:

- Multiple external clients need access
- You want to track usage per client
- IPs are dynamic or behind NAT

Contact the development team if API key authentication is needed.
