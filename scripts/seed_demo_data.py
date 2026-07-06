#!/usr/bin/env python
"""Wrapper to seed demo data via Django management command."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "backend"
cmd = [sys.executable, "manage.py", "seed_demo_data"]
subprocess.check_call(cmd, cwd=ROOT)
