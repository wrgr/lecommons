"""Guard the researcher/practitioner lens wiring and the extracted graph scripts.

These are file-content assertions (there is no JS test runner in this repo, mirroring
tests/test_graph_data.py): they check that the theme override, the pre-paint FOUC
script, the lens-visibility utilities, and the extracted Topic Map / focus graph init
functions are present, so a refactor can't silently drop them.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SRC = REPO_ROOT / "site" / "src"


def _read(rel: str) -> str:
    """Read a source file under site/src by relative path."""
    return (SRC / rel).read_text(encoding="utf-8")


def test_base_has_practitioner_theme_override() -> None:
    """Base.astro defines a practitioner lens that re-points the theme tokens."""
    base = _read("layouts/Base.astro")
    assert 'html[data-audience="practitioner"]' in base, "no practitioner theme block"
    assert "--font-body" in base and "--line" in base, "theme indirection tokens missing"


def test_base_has_prepaint_script() -> None:
    """Base.astro sets the audience attribute inline before first paint (FOUC fix)."""
    base = _read("layouts/Base.astro")
    assert "is:inline" in base, "pre-paint script must be inline or the flash returns"
    assert "lec-audience-mode" in base, "pre-paint script must read the stored lens"


def test_base_has_lens_visibility_utilities() -> None:
    """Base.astro ships the reusable per-lens content-visibility classes."""
    base = _read("layouts/Base.astro")
    assert ".lens-only--practitioner" in base
    assert ".lens-only--researcher" in base


def test_lens_chooser_is_mounted() -> None:
    """The first-run lens chooser component exists and is rendered in the shell."""
    assert (SRC / "components" / "LensChooser.astro").exists(), "LensChooser.astro missing"
    assert "<LensChooser" in _read("layouts/Base.astro"), "LensChooser not mounted in Base"


def test_graph_scripts_export_init() -> None:
    """The extracted client graph modules exist and export their entry points."""
    topic = _read("scripts/topicMap.ts")
    focus = _read("scripts/focusGraph.ts")
    assert "export function initTopicMap" in topic
    assert "export function initExploreGraph" in focus
    # The Topic Map panel gained an explicit "open topic page" navigation target.
    assert "detail-open" in topic


if __name__ == "__main__":
    test_base_has_practitioner_theme_override()
    test_base_has_prepaint_script()
    test_base_has_lens_visibility_utilities()
    test_lens_chooser_is_mounted()
    test_graph_scripts_export_init()
    print("lens assets OK")
