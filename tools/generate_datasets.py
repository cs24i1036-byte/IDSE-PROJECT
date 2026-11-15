"""Regenerate the generated CSV datasets (deterministic: same seeds -> identical files)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ds.dataset import DATA_DIR, build_all  # noqa: E402

for name, df in build_all().items():
    df.to_csv(DATA_DIR / name, index=False)
    print("wrote", name, df.shape)
