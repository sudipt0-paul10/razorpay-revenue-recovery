"""Child-stream RNG helper (Day 2 Stage 3).

Extends `rrx.sim.latent`'s frozen per-variable substream isolation to
per-message / per-engagement draws, WITHOUT creating a ninth top-level
substream and WITHOUT modifying `latent.py`'s frozen `SUBSTREAM_NAMES` or
`rng_for_substream`.

`seed_for_substream` already hashes whatever string it is given (only
`rng_for_substream` restricts the string to exact membership in the frozen
eight). This module reuses that same sha256 scheme with a `"<root>:<child>"`
string, so the resulting Generator is a genuinely independent RNG stream -
not a positional draw off the root substream's own single Generator, and
never threaded sequentially through anything else. Perturbing how many child
draws one arm takes therefore cannot shift another arm's draws, and child
index `k` always maps to the same seed regardless of how many other child
draws preceded it in this or any other run - the same CRN-isolation property
`substream_isolation: per_variable` already guarantees for the eight
top-level names, extended one level down.
"""

from __future__ import annotations

import numpy as np

from rrx.sim.latent import MASTER_SEED, SUBSTREAM_NAMES, seed_for_substream


def rng_for_child_stream(
    split: str, i: int, root: str, child: str, master_seed: int = MASTER_SEED
) -> np.random.Generator:
    """Independent Generator for (split, i, root, child).

    `root` must be one of the eight frozen top-level substream names (the
    same set `rng_for_substream` validates against) - this only adds a named
    child dimension beneath an existing root, never a new root.
    """
    if root not in SUBSTREAM_NAMES:
        raise KeyError(f"not a frozen substream name: {root!r}")
    return np.random.default_rng(seed_for_substream(split, i, f"{root}:{child}", master_seed))
