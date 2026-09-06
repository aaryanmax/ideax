#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Convenience launcher for the VAYU-CHRONICLE Pre-Boot Full Smoke Test.
Automatically detects and switches to 'C:\\Users\\Admin\\Projects\\.supervenv' if available.
"""

import os
import sys
import subprocess

SUPERVENV_PYTHON = os.path.abspath(r"C:\Users\Admin\Projects\.supervenv\Scripts\python.exe")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FULL_SMOKE_TEST_SCRIPT = os.path.join(SCRIPT_DIR, "scripts", "full_smoke_test.py")

def main():
    current_python = os.path.abspath(sys.executable)
    
    # Check if we should respawn in .supervenv
    in_supervenv = (
        SUPERVENV_PYTHON.lower() in current_python.lower() or
        r"\.supervenv" in os.environ.get("VIRTUAL_ENV", "").lower()
    )

    if not in_supervenv and os.path.exists(SUPERVENV_PYTHON) and "--no-respawn" not in sys.argv:
        print(f"\033[96m[*] Auto-activating .supervenv runtime: {SUPERVENV_PYTHON}\033[0m")
        cmd = [SUPERVENV_PYTHON, FULL_SMOKE_TEST_SCRIPT] + sys.argv[1:]
        try:
            res = subprocess.run(cmd)
            sys.exit(res.returncode)
        except Exception as e:
            print(f"\033[91m[-] Failed to auto-launch under .supervenv: {e}\033[0m")
            print("[*] Falling back to current Python environment...")

    # Otherwise execute directly in current Python process
    if os.path.exists(FULL_SMOKE_TEST_SCRIPT):
        # Insert backend directory into sys.path
        if SCRIPT_DIR not in sys.path:
            sys.path.insert(0, SCRIPT_DIR)
        
        from scripts.full_smoke_test import main as run_smoke_test
        run_smoke_test()
    else:
        print(f"Error: Could not find {FULL_SMOKE_TEST_SCRIPT}")
        sys.exit(1)

if __name__ == "__main__":
    main()
