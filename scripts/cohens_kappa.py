"""
Compute Cohen's kappa for inter-annotator agreement on detail_retention labels.
Reads research/data/annotation_template.csv (must have annotator1 and annotator2 columns filled).
"""

from __future__ import annotations

import csv
import pathlib
import sys

DATA_DIR = pathlib.Path(__file__).parent.parent / "research" / "data"


def compute_kappa(csv_path: pathlib.Path) -> float:
    try:
        from sklearn.metrics import cohen_kappa_score
    except ImportError:
        raise ImportError("scikit-learn required: pip install scikit-learn")

    ann1, ann2 = [], []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            v1 = row.get("detail_retention_annotator1", "").strip()
            v2 = row.get("detail_retention_annotator2", "").strip()
            if v1 and v2:
                ann1.append(v1)
                ann2.append(v2)

    if len(ann1) < 2:
        print("Need at least 2 annotated rows; fill annotation_template.csv first.")
        sys.exit(1)

    kappa = cohen_kappa_score(ann1, ann2)
    print(f"Cohen's kappa (detail_retention): {kappa:.4f}  (n={len(ann1)})")
    return kappa


if __name__ == "__main__":
    path = DATA_DIR / "annotation_template.csv"
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)
    compute_kappa(path)
