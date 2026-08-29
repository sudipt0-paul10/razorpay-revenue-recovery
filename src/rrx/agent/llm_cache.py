"""LLM cache (docs/A3-DESIGN.md §13).

Cache key: exactly `(template_version, model, temperature, prompt_hash)`.
Canonical artifact: `results/<run_id>/llm_cache.jsonl` - `load_jsonl`/
`to_jsonl_line` are (de)serialization helpers only; no path is ever
touched unless a caller supplies one explicitly (mirroring
`rrx.agent.ledger.to_json_line` / `rrx.spec.manifest.write_manifest`'s own
"caller supplies the path" pattern) - this module never writes into the
repository's real `results/` directory.

Replay contract, verbatim from §13: "any reproduction of a past run_id
must satisfy every LLM call from that run's cache. Cache-miss during exact
replay = hard failure, never a silent live re-call." "`--allow-live`:
required for any live call." Both rules are enforced here as exceptions a
caller cannot silently ignore - `CacheMissDuringReplayError` and
`LiveCallNotAllowedError` are raised by `rrx.agent.planner.invoke_planner`,
not returned as a sentinel value.

No `rrx.sim` import - this module has no structural need for one.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path


def compute_prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class CacheKey:
    """§13's cache key, exactly these four components, in this order."""

    template_version: str
    model: str
    temperature: float
    prompt_hash: str

    def to_json_dict(self) -> dict:
        return asdict(self)


class CacheMissDuringReplayError(RuntimeError):
    """§13: "Cache-miss during exact replay = hard failure, never a silent
    live re-call." Raised instead of falling through to a live call."""


class LiveCallNotAllowedError(RuntimeError):
    """§13: "--allow-live: required for any live call." Raised when a
    cache miss would require a live call but the caller did not pass
    allow_live=True."""


class LLMCache:
    """In-memory `CacheKey -> raw LLM output string` store.

    `replay=True` marks this cache as reproducing one specific past
    `run_id` - per §13, a miss under replay is always a hard failure,
    regardless of `allow_live`. This class only stores/retrieves; the
    replay-vs-live-vs-miss decision is made by
    `rrx.agent.planner.invoke_planner`, which is the only caller that also
    holds the `allow_live` flag.
    """

    def __init__(self, *, replay: bool = False) -> None:
        self._entries: dict[CacheKey, str] = {}
        self.replay = replay

    def __contains__(self, key: CacheKey) -> bool:
        return key in self._entries

    def __len__(self) -> int:
        return len(self._entries)

    def get(self, key: CacheKey) -> str | None:
        return self._entries.get(key)

    def put(self, key: CacheKey, raw_output: str) -> None:
        self._entries[key] = raw_output


def load_jsonl(path: str | Path) -> LLMCache:
    """Loads a §22 `results/<run_id>/llm_cache.jsonl` file into a
    replay-mode `LLMCache`. `path` is always supplied by the caller -
    never defaulted to the repository's real `results/` directory, so
    exercising this function cannot accidentally read a canonical cache."""
    cache = LLMCache(replay=True)
    text = Path(path).read_text(encoding="utf-8")
    for line in text.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        key = CacheKey(
            template_version=row["template_version"],
            model=row["model"],
            temperature=row["temperature"],
            prompt_hash=row["prompt_hash"],
        )
        cache.put(key, row["raw_output"])
    return cache


def to_jsonl_line(key: CacheKey, raw_output: str) -> str:
    """One `results/<run_id>/llm_cache.jsonl` line (§13's canonical
    artifact format). Not called by anything yet - no A3-LLM run
    orchestration exists in this pass, mirroring
    `rrx.agent.ledger.to_json_line`'s own "not called by the runner in
    this pass" framing."""
    return json.dumps({**key.to_json_dict(), "raw_output": raw_output}, sort_keys=True)
