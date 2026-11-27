"""Tests for the visualization module (rendered headless with the Agg backend)."""

import pytest

matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from mortables import cashflows, viz  # noqa: E402

RENTIERS = [
    {"age": 65, "annual_rent": 12000, "gender": "M", "birth_year": 1961},
    {"age": 72, "annual_rent": 8000, "gender": "F", "birth_year": 1954},
]

CHARTS = {
    "qx": lambda **kw: viz.plot_qx(["TH0002", "TF0002"], **kw),
    "qx_generational": lambda **kw: viz.plot_qx(["TGH05"], generation=1960, **kw),
    "survival": lambda **kw: viz.plot_survival(
        ["TGH05", "TGF05"], generation=1950, **kw
    ),
    "life_expectancy": lambda **kw: viz.plot_life_expectancy(
        ["TH0002", "TF0002"], **kw
    ),
    "comparison": lambda **kw: viz.plot_comparison(
        "TGH05", "TH0002", generation=1950, **kw
    ),
    "generations": lambda **kw: viz.plot_generations(
        "TGH05", generations=[1930, 1950, 1970], **kw
    ),
    "cashflows": lambda **kw: viz.plot_cashflows(
        cashflows.project(RENTIERS, table="TGH05", rate=0.02), **kw
    ),
}


@pytest.fixture(autouse=True)
def _no_open_figures():
    plt.close("all")
    yield
    plt.close("all")


@pytest.mark.parametrize("name", sorted(CHARTS))
def test_chart_returns_figure_with_data(name):
    fig = CHARTS[name]()
    assert isinstance(fig, Figure)
    ax = fig.axes[0]
    assert ax.lines or ax.patches, "chart is empty"


@pytest.mark.parametrize("name", sorted(CHARTS))
def test_chart_is_released_from_pyplot(name):
    """Avoids the double display in Jupyter and memory build-up in loops."""
    CHARTS[name]()
    assert plt.get_fignums() == []


@pytest.mark.parametrize("name", sorted(CHARTS))
def test_save(name, tmp_path):
    path = tmp_path / f"{name}.png"
    CHARTS[name](save=path)
    assert path.stat().st_size > 1000


def test_returned_figure_can_still_be_saved(tmp_path):
    fig = viz.plot_qx(["TH0002"])
    fig.savefig(tmp_path / "qx.pdf")
    assert (tmp_path / "qx.pdf").stat().st_size > 1000


def test_show_calls_pyplot_show(monkeypatch):
    called = []
    monkeypatch.setattr(plt, "show", lambda *a, **k: called.append(True))
    viz.plot_qx(["TH0002"], show=True)
    assert called == [True]


def test_generational_table_needs_generation():
    with pytest.raises(ValueError, match="generation"):
        viz.plot_qx(["TGH05"])


def test_cashflows_series_share_one_axis():
    fig = CHARTS["cashflows"]()
    assert len(fig.axes) == 1
