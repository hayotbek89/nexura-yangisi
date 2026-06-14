#!/usr/bin/env python
"""Quick import test for all fixed modules"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

errors = []

try:
    from nexura.models.schemas import Vulnerability, ScanResult, ScanPlan
    print("✅ Schemas imported successfully")
except Exception as e:
    errors.append(f"❌ Schemas: {e}")
    print(f"❌ Schemas: {e}")

try:
    from nexura.history_db import HistoryDB
    print("✅ HistoryDB imported successfully")
except Exception as e:
    errors.append(f"❌ HistoryDB: {e}")
    print(f"❌ HistoryDB: {e}")

try:
    from nexura.ai_engine import AIEngine
    print("✅ AIEngine imported successfully")
except Exception as e:
    errors.append(f"❌ AIEngine: {e}")
    print(f"❌ AIEngine: {e}")

try:
    from nexura.web.app import app
    print("✅ Web app imported successfully")
except Exception as e:
    errors.append(f"❌ Web app: {e}")
    print(f"❌ Web app: {e}")

if not errors:
    print("\n✅ All imports OK! No errors detected.")
    sys.exit(0)
else:
    print(f"\n❌ {len(errors)} error(s) found")
    sys.exit(1)

