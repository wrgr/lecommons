"""Guard the Experiments page and its nav wiring.

File-content assertions in the style of tests/test_lens_assets.py (there is no JS
test runner in this repo): they check that the experiments page exists, renders a
card grid from its inline data, and is linked from the top nav — so a refactor
can't silently drop the tab or its cards.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SRC = REPO_ROOT / "site" / "src"


def _read(rel: str) -> str:
    """Read a source file under site/src by relative path."""
    return (SRC / rel).read_text(encoding="utf-8")


def test_experiments_page_exists() -> None:
    """The experiments page exists and renders a card grid from inline data."""
    page = _read("pages/experiments.astro")
    assert "experiments" in page, "experiments data array missing"
    assert 'class="card"' in page, "no card markup on experiments page"
    assert 'target="_blank"' in page, "experiment links must open outbound"


def test_experiments_page_lists_each_experiment() -> None:
    """Every experiment URL is present so none is silently dropped."""
    page = _read("pages/experiments.astro")
    for url in (
        "calibratedjudgment.org",
        "experttrace.org",
        "neurotrailblazers.org",
        "wrgr.github.io/pop",
        "grayroncal.com",
    ):
        assert url in page, f"experiment link missing: {url}"


def test_experiments_linked_from_nav() -> None:
    """The top nav links to the experiments tab."""
    nav = _read("components/NavBar.astro")
    assert 'slug: "experiments"' in nav, "experiments tab not wired into NavBar"


def test_featured_paper_banner() -> None:
    """The featured paper is shown as a banner across the top and links out."""
    page = _read("pages/experiments.astro")
    assert "featured-banner" in page, "featured paper banner markup missing"
    assert "lens-concentration/blob/main/papers/show-your-work.pdf" in page, (
        "featured paper link missing"
    )


if __name__ == "__main__":
    test_experiments_page_exists()
    test_experiments_page_lists_each_experiment()
    test_experiments_linked_from_nav()
    test_featured_paper_banner()
    print("experiments page OK")
