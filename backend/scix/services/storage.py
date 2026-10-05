"""Cell-value storage (ADR 0001).

PostgreSQL holds metadata; cell values live in Parquet. The reason is not speed: it is
that a worksheet's values must be *rewritten* by every transformation while its
metadata -- column roles, units, provenance -- must not be. Keeping values in the same
tables as metadata means every transform is an UPDATE across both, and the metadata
history is lost.

Layout::

    {storage_dir}/datasets/{dataset_id}/{worksheet_id}/v{N}.parquet

``v{N}`` is the transformation ``seq`` that produced the file. Because seq is dense and
starts at 1, a missing file number is a gap in the chain, not a naming accident.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def _require_pandas() -> None:
    try:
        import pyarrow  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Parquet cell storage needs pyarrow. Install scix[storage]."
        ) from exc


def worksheet_dir(storage_dir: Path, dataset_id: str, worksheet_id: str) -> Path:
    return Path(storage_dir) / "datasets" / str(dataset_id) / str(worksheet_id)


def version_path(
    storage_dir: Path, dataset_id: str, worksheet_id: str, seq: int
) -> Path:
    return worksheet_dir(storage_dir, dataset_id, worksheet_id) / f"v{seq}.parquet"


def write_frame(
    storage_dir: Path, dataset_id: str, worksheet_id: str, seq: int, frame: pd.DataFrame
) -> str:
    """Persist a cell-value frame. Returns the storage key relative to ``storage_dir``.

    The index is dropped rather than stored: row identity in this product comes from
    position plus the transformation chain, and a persisted pandas index is a silent
    source of shifted rows after a filter.
    """
    _require_pandas()
    path = version_path(storage_dir, dataset_id, worksheet_id, seq)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.reset_index(drop=True).to_parquet(path, index=False, engine="pyarrow")
    return str(path.relative_to(storage_dir))


def read_frame(
    storage_dir: Path, dataset_id: str, worksheet_id: str, store_key: str
) -> pd.DataFrame:
    path = Path(storage_dir) / store_key
    if not path.exists():
        raise FileNotFoundError(
            f"worksheet values missing at {path}. The chain may have a gap: the Parquet "
            f"file for this seq was not written."
        )
    return pd.read_parquet(path, engine="pyarrow")


def latest_key(seq: int) -> str | None:
    """Storage key for a worksheet at a given applied ``seq``.

    None for seq 0 because the base (pre-transformation) file is stored directly on the
    worksheet's ``column_store_key``, not under a version name.
    """
    return None if seq <= 0 else f"__resolve_latest__{seq}"


def frame_to_records(frame: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    """JSON-safe rows for the API. NaN and NaT become None rather than the strings
    ``"nan"``/``"NaT"``, which would otherwise reach the browser and be rendered as
    text in the data grid."""
    import math

    subset = frame.head(limit) if limit is not None else frame

    def clean(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        try:
            import pandas as pd

            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass
        if hasattr(value, "isoformat"):
            return value.isoformat()
        if hasattr(value, "item"):
            return value.item()
        return value

    return [{str(k): clean(v) for k, v in row.items()} for row in subset.to_dict("records")]