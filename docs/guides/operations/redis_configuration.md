# Redis Configuration Guide

## Overview

Redis is used for distributed caching and rate limiting in the DSA-110 Continuum
Imaging Pipeline dashboard. This guide explains how to configure and use Redis.

## Installation

### Option 1: Docker (Recommended)

```bash
docker run -d \
  --name dsa110-redis \
  -p 6379:6379 \
  redis:7-alpine
```

### Option 2: System Package Manager

**Ubuntu/Debian:**

```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**macOS:**

```bash
brew install redis
brew services start redis
```

**CentOS/RHEL:**

```bash
sudo yum install redis
sudo systemctl start redis
sudo systemctl enable redis
```

## Configuration

### Environment Variables

Set the Redis connection URL in your environment:

```bash
# Default local Redis
export REDIS_URL="redis://localhost:6379/0"

# Redis with password
export REDIS_URL="redis://:password@localhost:6379/0"

# Redis with custom host/port
export REDIS_URL="redis://redis.example.com:6379/0"

# Redis with SSL
export REDIS_URL="rediss://localhost:6379/0"
```

### Production Configuration

For production, configure Redis with:

1. **Password Authentication:**

```bash
# In redis.conf
requirepass your_strong_password_here
```

2. **Persistence:**

```bash
# In redis.conf
save 900 1      # Save after 900 seconds if at least 1 key changed
save 300 10     # Save after 300 seconds if at least 10 keys changed
save 60 10000   # Save after 60 seconds if at least 10000 keys changed
```

3. **Memory Limits:**

```bash
# In redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru  # Evict least recently used keys
```

## Verification

### Test Redis Connection

```python
import redis

# Test connection
try:
    r = redis.from_url("redis://localhost:6379/0")
    r.ping()
    print("✓ Redis connection successful")
except Exception as e:
    print(f"✗ Redis connection failed: {e}")
```

### Test from Command Line

```bash
# Connect to Redis CLI
redis-cli

# Test ping
127.0.0.1:6379> PING
PONG

# Check info
127.0.0.1:6379> INFO stats
```

## Monitoring

### Redis CLI Commands

```bash
# Check memory usage
redis-cli INFO memory

# Check connected clients
redis-cli INFO clients

# Check keyspace
redis-cli INFO keyspace

# Monitor commands in real-time
redis-cli MONITOR
```

### Python Monitoring

```python
from dsa110_contimg.api.caching import get_cache

cache = get_cache()
stats = cache.get_stats()
print(f"Backend: {stats['backend']}")
print(f"Keys: {stats['keys']}")
print(f"Hits: {stats['hits']}")
print(f"Misses: {stats['misses']}")
```

## Fallback Behavior

If Redis is not available or connection fails:

- **Caching**: Falls back to in-memory cache (single instance only)
- **Rate Limiting**: Falls back to in-memory limiter (single instance only)

The system will log warnings but continue to function. Check logs for:

- "Failed to connect to Redis: ..."
- "Using in-memory cache fallback"
- "Rate limiter initialized with in-memory storage"

## Troubleshooting

### Connection Refused

**Problem:** `Connection refused` error

**Solutions:**

1. Check if Redis is running: `redis-cli ping`
2. Check Redis port: `netstat -tuln | grep 6379`
3. Check firewall rules
4. Verify `REDIS_URL` environment variable

### Authentication Failed

**Problem:** `NOAUTH Authentication required`

**Solutions:**

1. Include password in `REDIS_URL`: `redis://:password@localhost:6379/0`
2. Check Redis password configuration in `redis.conf`

### Memory Issues

**Problem:** Redis running out of memory

**Solutions:**

1. Increase `maxmemory` in `redis.conf`
2. Adjust `maxmemory-policy` (e.g., `allkeys-lru`)
3. Monitor key expiration and TTL settings

## Production Recommendations

1. **Use Redis Sentinel** for high availability
2. **Enable persistence** (RDB or AOF) for data durability
3. **Set memory limits** to prevent OOM
4. **Use password authentication** for security
5. **Monitor performance** with Redis monitoring tools
6. **Backup regularly** using `BGSAVE` or persistence

## Related Documentation

- [Performance & Scalability Guide](performance_and_scalability.md)
- [Redis Official Documentation](https://redis.io/docs/)
