# the-M Auth Service

Authentication and IAM microservice for the-M. Runs as `them-auth-service` on port **8701**.
Owns the `auth_service` schema in the shared `them` Postgres database.

## Responsibilities

- Username/password login → JWT access + refresh tokens (httpOnly cookies)
- JWT verification for the bridge and frontend
- User, role, team, and session management
- Audit logging of all auth events

## Cookies set on login

| Cookie | Purpose |
|---|---|
| `them_access_token` | Short-lived JWT (2h) — read by bridge + frontend proxy |
| `them_refresh_token` | Long-lived refresh (7d) — used by `/auth/refresh` |

## Key endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/auth/login` | Username+password → sets cookies |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/logout` | Clears cookies, blacklists tokens |
| GET | `/auth/me` | Returns current user from JWT |
| GET | `/health` | Health check |

## Auth schema tables

`roles`, `users`, `teams`, `team_members`, `user_overrides`, `auth_audit`, `user_sessions`, `blacklisted_tokens`

**Never query these tables directly from the bridge.** Use `app/services/auth_client.py` (HTTP to port 8701).

## Local dev credentials

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | super_admin |
| `avi` | `avi123` | super_admin |

See `docs/AUTH.md` for full auth flow documentation.
