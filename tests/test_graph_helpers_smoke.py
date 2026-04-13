"""Smoke test for pure graph helper functions (runs Node on app/graph.js)."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


class GraphHelpersSmokeTests(unittest.TestCase):
    def test_graph_js_helpers(self) -> None:
        snippet = """
import { buildNeighborIndex, matchesGraphNodeFilters, browseGroupKey } from './app/graph.js';
const ix = buildNeighborIndex([{ source: 'a', target: 'b' }]);
if (!ix.get('a').has('b')) process.exit(1);
const n = { id: 'a', label: 'Hi', type: 'topic' };
if (!matchesGraphNodeFilters(n, 'hi', 'all', ix, null)) process.exit(2);
if (browseGroupKey({ type: 'topic_part' }) !== 'topic') process.exit(3);
"""
        proc = subprocess.run(
            ["node", "--input-type=module", "-e", snippet],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)


if __name__ == "__main__":
    unittest.main()
