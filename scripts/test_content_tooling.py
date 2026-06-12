"""Stub tests for the registry build and MDX ref validation tooling (plain python3 runnable)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_registry
import validate_mdx_refs


def test_normalise_secondary_topics() -> None:
    """String and list inputs normalise to clean topic lists."""
    assert build_registry.normalise_secondary_topics("T01, T02") == ["T01", "T02"]
    assert build_registry.normalise_secondary_topics(["T03", ""]) == ["T03"]
    assert build_registry.normalise_secondary_topics(None) == []


def test_yaml_ids_cover_committed_refs() -> None:
    """Every LE ref in committed MDX resolves against the landscape/data exports."""
    ids = validate_mdx_refs.load_yaml_ids()
    assert ids, "landscape/data exports should yield at least one resource id"
    _total, pairs, _non_le = validate_mdx_refs.scan_mdx()
    orphans = sorted({r for _p, r in pairs if r not in ids})
    assert not orphans, f"orphaned refs: {orphans}"


if __name__ == "__main__":
    test_normalise_secondary_topics()
    test_yaml_ids_cover_committed_refs()
    print("ok")
