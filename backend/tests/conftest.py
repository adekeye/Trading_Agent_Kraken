import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Deterministic test secrets so encryption_key derivation is stable across runs.
os.environ.setdefault("JWT_SECRET", "test-secret-do-not-use-in-prod")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-must-be-long-enough")

# Use a per-process temp file so tables persist across threads (TestClient runs
# the app in a separate thread; in-memory sqlite would not be shared).
_TMP_DB = Path(tempfile.gettempdir()) / "kta_test.db"
if _TMP_DB.exists():
    _TMP_DB.unlink()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TMP_DB}")

# Keep the test suite offline: do not let the FastAPI lifespan spawn the
# background xStocks refresh that hits Kraken's real public endpoint.
os.environ.setdefault("EQUITY_REGISTRY_AUTO_REFRESH", "false")
