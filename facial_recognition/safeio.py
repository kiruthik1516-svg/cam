"""Safe loading of .npz files.

``numpy.load(..., allow_pickle=True)`` can run arbitrary code from a tampered file, so pickle is off by default.
Arrays of strings are stored as plain unicode arrays, which need no pickle. Old files written with object arrays
(pickle) can still be read by setting ALLOW_PICKLE_NPZ=1, but only do that for files you created yourself.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict

import numpy as np

logger = logging.getLogger(__name__)


class LoadedArrays(Dict[str, Any]):
    """All arrays of an .npz file, read eagerly. Supports ``name in x``, ``x[name]`` and ``with`` like NpzFile."""

    def __enter__(self) -> "LoadedArrays":
        return self

    def __exit__(self, *exc: Any) -> bool:
        return False

    @property
    def files(self) -> list:
        return list(self.keys())


def _read_all(path: str | Path, allow_pickle: bool) -> LoadedArrays:
    with np.load(path, allow_pickle=allow_pickle) as npz:
        # NpzFile is lazy: object (pickled) arrays only fail when they are read, so read everything here.
        return LoadedArrays({name: npz[name] for name in npz.files})


def load_npz(path: str | Path) -> LoadedArrays:
    """Load an .npz without pickle. Raises ValueError for legacy pickled files unless ALLOW_PICKLE_NPZ is set."""
    try:
        return _read_all(path, allow_pickle=False)
    except ValueError:
        if os.environ.get("ALLOW_PICKLE_NPZ", "").strip().lower() in ("1", "true", "yes"):
            logger.warning(
                "Loading %s with pickle enabled (ALLOW_PICKLE_NPZ). Only do this for files you created.", path
            )
            return _read_all(path, allow_pickle=True)
        logger.error(
            "%s was saved with pickled (object) arrays, which are not loaded for safety. "
            "Re-create it (re-run enrollment / let the gallery re-sync), or set ALLOW_PICKLE_NPZ=1 if you trust the file.",
            path,
        )
        raise
