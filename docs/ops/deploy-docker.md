# Deploy with Docker Compose

- Copy `.env`: `cp ops/docker/.env.example ops/docker/.env`; edit absolute paths and UID/GID
- Build: `make compose-build`
- Up: `make compose-up`
- Logs: `make compose-logs SERVICE=stream`
- Optional scheduler: `make compose-up-scheduler`
