#!/usr/bin/env python3
"""Healthcheck script for ecocupon-api Docker container."""
import sys
try:
    from urllib.request import urlopen
    r = urlopen("http://localhost:9002/health", timeout=5)
    sys.exit(0 if r.status == 200 else 1)
except Exception:
    sys.exit(1)
