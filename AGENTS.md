# You2API

OpenAI-compatible API proxy for You.com AI service. Single Go binary, no database.

## Cursor Cloud specific instructions

### Build & Run

```bash
go build -o main . && ./main
```

Server listens on `:8080` by default (configurable via `PORT` env var).

### Key Endpoints

- `GET /` — health check
- `GET /v1/models` — list available AI models
- `POST /v1/chat/completions` — chat completion (requires `Authorization: Bearer <DS_TOKEN>`)

### Lint & Test

- **Lint:** `go vet ./...`
- **Test:** `go test ./... -timeout 8s` — the existing `start_test.go` calls `run()` which starts the HTTP server and blocks until timeout. This is a pre-existing test design issue; the panic on timeout is expected.

### Gotchas

- The `/v1/chat/completions` endpoint requires a valid You.com `DS` session token as the Bearer token. Without it, the proxy connects to You.com but returns empty content.
- `start_test.go` is effectively an integration test that starts a real server. Run with `-timeout` flag to avoid hanging.
- Docker Compose is available (`docker-compose.yml`) for running with optional Prometheus + Grafana monitoring, but is not needed for basic development.
