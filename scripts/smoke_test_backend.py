#Owner::ANIKET::ANHOTRA = MR.Panda
"""Starts the real server on a SQLite file, uses it over HTTP, restarts it, checks persistence.

Covers: migration, startup, health, registration, login, wrong password, validation error,
security headers, login lockout, and that data survives a server restart.
Exits with status 1 and a message on any failure. Run it from the project root.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PORT = 8765
BASE = f"http://127.0.0.1:{PORT}"


def require(condition: bool, message: str) -> None:
    """Stop with a clear message when a check fails."""
    if not condition:
        print("FAIL: " + message)
        sys.exit(1)
    print("ok:   " + message)


def call(
    method: str, path: str, body: dict[str, Any] | None = None, token: str | None = None
) -> tuple[int, dict[str, Any], Any]:
    """Send one HTTP request and return (status, json body, headers)."""
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else {}, response.headers
    except urllib.error.HTTPError as error:
        raw = error.read()
        return error.code, json.loads(raw) if raw else {}, error.headers


def start_server(environment: dict[str, str]) -> subprocess.Popen[bytes]:
    """Start uvicorn with the application factory and wait until /health answers."""
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(PORT),
        ],
        cwd=ROOT / "backend",
        env=environment,
    )
    for _ in range(50):
        try:
            if call("GET", "/health")[0] == 200:
                return process
        except OSError:
            time.sleep(0.2)
    process.kill()
    require(False, "server did not become healthy within 10 seconds")
    return process


def main() -> None:
    """Run the whole smoke test."""
    folder = tempfile.mkdtemp(prefix="sitepay_smoke_")
    environment = dict(os.environ)
    environment.update(
        {
            "DATABASE_URL": f"sqlite:///{folder}/smoke.sqlite3",
            "SECRET_KEY": "smoke-test-secret-key-long-enough-123456",
            "APPLICATION_ENVIRONMENT": "development",
            "LOGIN_MAX_FAILURES": "3",
        }
    )
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT / "backend",
        env=environment,
        check=True,
    )
    print("ok:   alembic upgrade head on a fresh SQLite file")
    server = start_server(environment)
    try:
        status, body, headers = call("GET", "/health")
        require(status == 200 and body["status"] == "ok", "GET /health is ok")
        require(headers.get("X-Content-Type-Options") == "nosniff", "security headers present")
        require(call("GET", "/health/ready")[0] == 200, "GET /health/ready reaches the database")
        user = {
            "email": "smoke@example.com",
            "password": "strongpass123",
            "name": "Smoke",
            "organization_name": "Smoke Builders",
        }
        require(call("POST", "/api/v1/auth/register", user)[0] == 201, "register returns 201")
        require(call("POST", "/api/v1/auth/register", user)[0] == 409, "duplicate email gives 409")
        bad = dict(user, email="not-an-email")
        require(call("POST", "/api/v1/auth/register", bad)[0] == 422, "invalid email gives 422")
        credentials = {"email": user["email"], "password": user["password"]}
        status, tokens, _ = call("POST", "/api/v1/auth/login", credentials)
        require(status == 200 and "access_token" in tokens, "login returns tokens")
        status, me, _ = call("GET", "/api/v1/auth/me", token=tokens["access_token"])
        require(status == 200 and me["user"]["email"] == user["email"], "GET /auth/me works")
        require(call("GET", "/api/v1/auth/me")[0] == 401, "no token gives 401")
        server.terminate()
        server.wait(timeout=10)
        server = start_server(environment)
        status, again, _ = call("POST", "/api/v1/auth/login", credentials)
        require(status == 200, "login works after a server restart (data persisted)")
        wrong = dict(credentials, password="wrongpassword1")
        codes = [call("POST", "/api/v1/auth/login", wrong)[0] for _ in range(3)]
        require(codes == [401, 401, 401], "wrong password gives 401 until the limit")
        status, _, headers = call("POST", "/api/v1/auth/login", wrong)
        require(status == 429 and headers.get("Retry-After") is not None, "lockout gives 429")
        require(
            call("POST", "/api/v1/auth/login", credentials)[0] == 429, "lock holds for the pair"
        )
    finally:
        server.terminate()
        server.wait(timeout=10)
    print("All smoke checks passed.")


if __name__ == "__main__":
    main()
