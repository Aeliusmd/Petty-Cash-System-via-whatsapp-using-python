"""
Configuration module for shared paths and settings
"""
from pathlib import Path

# Determine receipts directory (same logic as main.py)
possible_paths = [
    Path("/app/backend/receipts"),  # Docker
    Path(__file__).resolve().parent.parent / "receipts",  # Local development
    Path("receipts").resolve()  # Fallback
]

RECEIPTS_DIR = None
for path in possible_paths:
    if path.exists():
        RECEIPTS_DIR = path
        break

if not RECEIPTS_DIR:
    # Fallback to creating one relative to file
    RECEIPTS_DIR = possible_paths[1]
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)

print(f"📁 Config: RECEIPTS_DIR = {RECEIPTS_DIR}")
