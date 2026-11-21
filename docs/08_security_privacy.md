# Security and Privacy Plan (Phase 1 state)

Rules reference: `PROJECT_RULES.md` section E. This document separates controls that **exist in code**, controls that
were **tested by running tests**, and gaps. Nothing is claimed as verified unless a test run backs it.

## Controls in place

| Area | What exists | Tested by running? |
|---|---|---|
| Passwords | scrypt (cost 32768), random salt, constant time compare, Unicode normalisation, rehash on weaker parameters, length limits, tampered hashes fail safely | Yes |
| Unknown email timing | Dummy hash check so response time does not reveal which emails exist | Function runs. Timing equality not measured |
| Login tokens | Signed tokens, algorithm fixed in code, required claims, access and refresh types cannot be swapped, "none" algorithm refused | Yes |
| Rate limiting | Login locks for 15 minutes after 5 failures per email and address, and an address after 20 failures. 10 registrations per address per hour. Forwarded headers are ignored unless trusted proxies are configured | Logic tested with a fake clock. Route wiring **not run** |
| Refresh tokens | Single use with rotation. Reusing an old token revokes all of that user's tokens | Logic written. **Not run** (needs database) |
| Settings | Secret key must be 32+ characters and not a placeholder. Staging and production refuse SQLite | Yes |
| Roles | Owner, manager, engineer, accounts, worker with a permission matrix. Last owner cannot be removed or demoted | Matrix tested. Routes **not run** |
| Tenant separation | Every query filters by organisation. Another company's records answer "not found" | Queries written. **Not run** |
| Audit trail | Hash chained, append only, with database triggers | Chain logic and SQLite triggers tested. Writing through the app **not run** |
| Approval control | Only a person in a deciding role can approve or reject. Agents and the system cannot | Yes |
| Input validation | Strict request formats, unknown fields refused, exact decimal money, floats refused | Yes |
| Errors | One error shape. Unexpected errors are logged in full but the client sees a generic message | Shape tested. Handler **not run** |
| Response headers | nosniff, no framing, no referrer, no caching of API replies | **Not run** |
| Secrets | Read from environment only. `.env` is ignored by git. Compose file takes secrets from environment | Compose file checked for hard coded secrets |
| API docs | Switched off in production | **Not run** |

## Known gaps (not built, do not rely on them)

- Rate limiting is held in memory in each server process. With several processes the limits multiply, and guessing spread across many addresses is not stopped. A shared store (database or Redis) and alerting are planned. Behind a reverse proxy, `TRUSTED_PROXY_COUNT` must be set correctly or all users share one address.
- No password reset or email verification (behind the `password_reset` feature flag, not built).
- Anyone can register a new organisation. Invitations for people without accounts are not built.
- Access tokens cannot be revoked before they expire (default 30 minutes). Refresh tokens can.
- No encryption at rest or TLS configuration. These belong to deployment (Phase 9).
- No face blurring, data export or data deletion on request (rule E3 and E5), and no data protection law review (rule E7).
- No cross-site request settings (CORS) yet, because the frontend does not exist.
- No dependency vulnerability scanning in continuous integration yet. SP-06 Sentinel is expected to add it.
- Request logging does not record bodies or tokens, but a dedicated test that logs contain no secrets does not exist yet.

## Privacy

Only name, email, language and role are stored for a user. Site photos, voice notes and bank details do not exist yet,
and when they do, rules E3 and E6 apply (face blurring and masked financial details).
