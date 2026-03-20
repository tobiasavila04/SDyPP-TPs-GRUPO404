"""
Health Check — puerto 5010
Verifica si cada servidor HIT está escuchando en su puerto correspondiente.
"""

import socket
import time
from datetime import datetime, timezone

from fastapi import FastAPI

SERVICES = [
    {"name": "hit1-server",  "hit": 1, "port": 5000, "proto": "TCP"},
    {"name": "hit2-server",  "hit": 2, "port": 5001, "proto": "TCP"},
    {"name": "hit3-server",  "hit": 3, "port": 5002, "proto": "TCP"},
    {"name": "hit4-node-c1", "hit": 4, "port": 5003, "proto": "TCP"},
    {"name": "hit4-node-c2", "hit": 4, "port": 5004, "proto": "TCP"},
    {"name": "hit5-node-c1", "hit": 5, "port": 5003, "proto": "TCP"},
    {"name": "hit5-node-c2", "hit": 5, "port": 5004, "proto": "TCP"},
    {"name": "hit6-node-d",  "hit": 6, "port": 5005, "proto": "TCP"},
    {"name": "hit7-node-d",  "hit": 7, "port": 5006, "proto": "TCP"},
    {"name": "hit8-node-d",  "hit": 8, "port": 5007, "proto": "gRPC"},
]

_start_time = time.time()

app = FastAPI(title="SD2026-GRUPO404 — HIT Health Check", version="1.0.0")


def _port_is_listening(port: int, timeout: float = 1.0) -> bool:
    """Intenta conectarse al puerto en localhost. True si está escuchando."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


@app.get("/health")
def health():
    results = {}
    for svc in SERVICES:
        up = _port_is_listening(svc["port"])
        results[svc["name"]] = {
            "hit": svc["hit"],
            "port": svc["port"],
            "proto": svc["proto"],
            "status": "up" if up else "down",
        }

    all_up = all(v["status"] == "up" for v in results.values())

    return {
        "status": "healthy" if all_up else "degraded",
        "uptime_seconds": round(time.time() - _start_time, 1),
        "services": results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
