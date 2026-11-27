"""
Visualization — standard actuarial mortality charts.

All functions return a ``matplotlib.figure.Figure`` so they can be displayed
interactively or saved to file.

Requires ``matplotlib`` (optional dependency).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Sequence, Union

import numpy as np

if TYPE_CHECKING:  # pragma: no cover
    import pandas

from .core import MortalityTable, get_table


def _ensure_matplotlib():
    try:
        import matplotlib.pyplot as plt

        return plt
    except ImportError:
        raise ImportError(
            "matplotlib is required for visualization. "
            "Install it with:  pip install mortables[viz]"
        )


def _resolve_tables(
    tables: Sequence[Union[str, MortalityTable]],
    generation: Optional[int] = None,
) -> List[MortalityTable]:
    """Convert a mix of table IDs and MortalityTable objects."""
    result = []
    for t in tables:
        if isinstance(t, str):
            result.append(get_table(t, generation=generation))
        else:
            result.append(t)
    return result


# ---------------------------------------------------------------------------
# 1. Mortality curve: log(qx) vs age
# ---------------------------------------------------------------------------

def plot_qx(
    tables: Sequence[Union[str, MortalityTable]],
    log_scale: bool = True,
    age_range: Optional[tuple] = None,
    generation: Optional[int] = None,
    title: Optional[str] = None,
    figsize: tuple = (10, 6),
):
    """
    Plot mortality rates qx for one or more tables.

    Parameters
    ----------
    tables : list of str or MortalityTable
        Tables to plot (e.g. ``["TH0002", "TF0002"]``).
    log_scale : bool
        If ``True`` (default), use logarithmic y-axis.
    age_range : tuple of (min_age, max_age), optional
        Restrict the x-axis.
    generation : int, optional
        Birth year for generational tables.
    title : str, optional
    figsize : tuple

    Returns
    -------
    matplotlib.figure.Figure
    """
    plt = _ensure_matplotlib()
    resolved = _resolve_tables(tables, generation)

    fig, ax = plt.subplots(figsize=figsize)
    for tbl in resolved:
        ages = tbl.ages
        qx = tbl.qx
        if age_range:
            mask = (ages >= age_range[0]) & (ages <= age_range[1])
            ages = ages[mask]
            qx = qx[mask]
        ax.plot(ages, qx, label=tbl.name, linewidth=1.5)

    if log_scale:
        ax.set_yscale("log")
    ax.set_xlabel("Âge", fontsize=12)
    ax.set_ylabel("qx (probabilité de décès)", fontsize=12)
    ax.set_title(title or "Courbe de mortalité", fontsize=14)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# 2. Survival curve: lx or S(x) vs age
# ---------------------------------------------------------------------------

def plot_survival(
    tables: Sequence[Union[str, MortalityTable]],
    age_range: Optional[tuple] = None,
    generation: Optional[int] = None,
    normalize: bool = True,
    title: Optional[str] = None,
    figsize: tuple = (10, 6),
):
    """
    Plot survival curves lx (or normalized to 1.0).

    Parameters
    ----------
    tables : list of str or MortalityTable
    age_range : tuple, optional
    generation : int, optional
    normalize : bool
        If ``True``, lx is divided by the radix so the curve starts at 1.0.
    title : str, optional
    figsize : tuple

    Returns
    -------
    matplotlib.figure.Figure
    """
    plt = _ensure_matplotlib()
    resolved = _resolve_tables(tables, generation)

    fig, ax = plt.subplots(figsize=figsize)
    for tbl in resolved:
        ages = tbl.ages
        lx = tbl.lx.astype(float)
        if normalize:
            first = lx[tbl.min_age] if tbl.min_age <= tbl.max_age else 0.0
            if first > 0:
                lx = lx / first
        if age_range:
            mask = (ages >= age_range[0]) & (ages <= age_range[1])
            ages = ages[mask]
            lx = lx[mask]
        ax.plot(ages, lx, label=tbl.name, linewidth=1.5)

    ax.set_xlabel("Âge", fontsize=12)
    ylabel = "Proportion de survivants" if normalize else "lx (survivants)"
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title or "Courbe de survie", fontsize=14)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# 3. Life expectancy by age
# ---------------------------------------------------------------------------

def plot_life_expectancy(
    tables: Sequence[Union[str, MortalityTable]],
    age_range: Optional[tuple] = (0, 100),
    generation: Optional[int] = None,
    title: Optional[str] = None,
    figsize: tuple = (10, 6),
):
    """
    Plot curtate life expectancy ex as a function of age.

    Parameters
    ----------
    tables : list of str or MortalityTable
    age_range : tuple
    generation : int, optional
    title : str, optional
    figsize : tuple

    Returns
    -------
    matplotlib.figure.Figure
    """
    plt = _ensure_matplotlib()
    resolved = _resolve_tables(tables, generation)

    fig, ax = plt.subplots(figsize=figsize)
    for tbl in resolved:
        ages = tbl.ages
        ex = tbl.ex
        if age_range:
            mask = (ages >= age_range[0]) & (ages <= age_range[1])
            ages = ages[mask]
            ex = ex[mask]
        ax.plot(ages, ex, label=tbl.name, linewidth=1.5)

    ax.set_xlabel("Âge", fontsize=12)
    ax.set_ylabel("Espérance de vie résiduelle (années)", fontsize=12)
    ax.set_title(title or "Espérance de vie par âge", fontsize=14)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# 4. Table comparison (bar chart of qx ratios)
# ---------------------------------------------------------------------------

def plot_comparison(
    table_a: Union[str, MortalityTable],
    table_b: Union[str, MortalityTable],
    age_range: tuple = (30, 90),
    generation: Optional[int] = None,
    title: Optional[str] = None,
    figsize: tuple = (12, 6),
):
    """
    Compare two tables by plotting the ratio qx_A / qx_B.

    A ratio > 1 means table A has higher mortality than table B.

    Parameters
    ----------
    table_a, table_b : str or MortalityTable
    age_range : tuple
    generation : int, optional
    title : str, optional
    figsize : tuple

    Returns
    -------
    matplotlib.figure.Figure
    """
    plt = _ensure_matplotlib()
    a = _resolve_tables([table_a], generation)[0]
    b = _resolve_tables([table_b], generation)[0]

    min_age, max_age = age_range
    ages = np.arange(min_age, max_age + 1)

    def _qx(tbl, age):
        return tbl.qx[age] if age <= tbl.max_age else np.nan

    ratios = []
    for age in ages:
        qa, qb = _qx(a, age), _qx(b, age)
        ok = not (np.isnan(qa) or np.isnan(qb)) and qb > 0
        ratios.append(qa / qb if ok else np.nan)

    ratios = np.array(ratios)

    fig, ax = plt.subplots(figsize=figsize)
    colors = ["#e74c3c" if r > 1 else "#2ecc71" for r in ratios]
    ax.bar(ages, ratios, color=colors, alpha=0.7, width=0.8)
    ax.axhline(y=1.0, color="black", linestyle="--", linewidth=1)
    ax.set_xlabel("Âge", fontsize=12)
    ax.set_ylabel(f"Ratio qx ({a.name} / {b.name})", fontsize=12)
    ax.set_title(
        title or f"Comparaison de mortalité : {a.name} vs {b.name}",
        fontsize=14,
    )
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# 5. Cash flow projection chart
# ---------------------------------------------------------------------------

def plot_cashflows(
    flows: "pandas.DataFrame",
    show_pv: bool = True,
    title: Optional[str] = None,
    figsize: tuple = (12, 6),
):
    """
    Plot projected cash flows from :func:`mortables.cashflows.project`.

    Parameters
    ----------
    flows : pandas.DataFrame
        Output of ``cashflows.project()``.
    show_pv : bool
        If ``True``, overlay the present-value line.
    title : str, optional
    figsize : tuple

    Returns
    -------
    matplotlib.figure.Figure
    """
    plt = _ensure_matplotlib()

    fig, ax1 = plt.subplots(figsize=figsize)

    ax1.bar(
        flows["year"],
        flows["expected_payment"],
        color="#3498db",
        alpha=0.6,
        label="Paiement attendu",
    )
    ax1.set_xlabel("Année", fontsize=12)
    ax1.set_ylabel("Paiement attendu (€)", fontsize=12, color="#3498db")

    if show_pv:
        ax2 = ax1.twinx()
        ax2.plot(
            flows["year"],
            flows["pv_payment"],
            color="#e74c3c",
            linewidth=2,
            label="Valeur actualisée",
        )
        ax2.set_ylabel("Valeur actualisée (€)", fontsize=12, color="#e74c3c")

    ax1.set_title(title or "Projection des flux de trésorerie", fontsize=14)
    ax1.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# 6. Generational comparison: same table, multiple generations
# ---------------------------------------------------------------------------

def plot_generations(
    table_id: str,
    generations: Sequence[int],
    log_scale: bool = True,
    age_range: Optional[tuple] = (50, 100),
    title: Optional[str] = None,
    figsize: tuple = (10, 6),
):
    """
    Compare mortality across generations for a generational table.

    Parameters
    ----------
    table_id : str
        Generational table (``"TGH05"`` or ``"TGF05"``).
    generations : list of int
        Birth years to compare.
    log_scale : bool
    age_range : tuple, optional
    title : str, optional
    figsize : tuple

    Returns
    -------
    matplotlib.figure.Figure
    """
    tables = [get_table(table_id, generation=g) for g in generations]
    return plot_qx(
        tables,
        log_scale=log_scale,
        age_range=age_range,
        title=title or f"Mortalité par génération ({table_id})",
        figsize=figsize,
    )
