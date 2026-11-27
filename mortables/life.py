"""
Actuarial life functions — commutation numbers, annuities, and insurance values.

All functions take a :class:`~mortables.core.MortalityTable` and a technical
interest rate as inputs.

Notation follows the International Actuarial Notation:
  Dx, Nx, Cx, Mx — commutation numbers
  äx — annuity-due
  ax — annuity-immediate
  Ax — whole life insurance
  äx:n⌉ — temporary annuity
  Ax:n⌉ — term insurance
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from .core import MortalityTable


# ---------------------------------------------------------------------------
# Commutation numbers
# ---------------------------------------------------------------------------
@dataclass
class CommutationTable:
    """Pre-computed commutation numbers for a given table and interest rate.

    Attributes
    ----------
    Dx, Nx, Sx, Cx, Mx, Rx : np.ndarray
        Classical commutation columns.
    rate : float
        Technical interest rate used.
    table_name : str
        Name of the underlying mortality table.
    """

    Dx: np.ndarray
    Nx: np.ndarray
    Sx: np.ndarray
    Cx: np.ndarray
    Mx: np.ndarray
    Rx: np.ndarray
    rate: float
    table_name: str


def _check_rate(rate: float) -> float:
    rate = float(rate)
    if not rate > -1.0:
        raise ValueError(f"rate must be > -1, got {rate}")
    return rate


def _check_term(term) -> int:
    if isinstance(term, bool) or not float(term).is_integer() or term < 0:
        raise ValueError(f"term must be a non-negative integer, got {term!r}")
    return int(term)


def commutation(table: MortalityTable, rate: float) -> CommutationTable:
    """
    Compute the full set of commutation numbers.

    Results are cached on the table for each rate, so repeated calls
    (annuities, premiums, reserves) do not recompute them.

    Parameters
    ----------
    table : MortalityTable
    rate : float
        Annual technical interest rate (e.g. 0.02 for 2 %).  Negative rates
        are allowed (must be > -1).

    Returns
    -------
    CommutationTable
        Columns are ``NaN`` at ages where the table is not defined.
    """
    rate = _check_rate(rate)
    key = ("commutation", rate)
    cached = table._cache.get(key)
    if cached is not None:
        return cached

    v = 1.0 / (1.0 + rate)  # discount factor
    ages = table.ages.astype(float)
    lx = table.lx.astype(float)

    # Dx = lx · v^x
    Dx = lx * v ** ages

    # Cx = dx · v^(x+1)  where dx = lx · qx
    Cx = lx * table.qx * v ** (ages + 1)

    def _rev_cumsum(a: np.ndarray) -> np.ndarray:
        return np.flip(np.cumsum(np.flip(a)))

    Nx = _rev_cumsum(Dx)
    Sx = _rev_cumsum(Nx)
    Mx = _rev_cumsum(Cx)
    Rx = _rev_cumsum(Mx)

    ct = CommutationTable(
        Dx=Dx, Nx=Nx, Sx=Sx, Cx=Cx, Mx=Mx, Rx=Rx,
        rate=rate, table_name=table.name,
    )
    table._cache[key] = ct
    return ct


def _prepare(table: MortalityTable, age, rate: float):
    """Validate inputs and return (commutation table, age)."""
    age = table.check_age(age)
    return commutation(table, rate), age


# ---------------------------------------------------------------------------
# Life expectancy
# ---------------------------------------------------------------------------

def life_expectancy(table: MortalityTable, age: int = 0) -> float:
    """
    Curtate life expectancy at a given age.

    This is the expected number of **complete** future years of life.

    Parameters
    ----------
    table : MortalityTable
    age : int

    Returns
    -------
    float
    """
    return table.life_expectancy(age)


# ---------------------------------------------------------------------------
# Annuities
# ---------------------------------------------------------------------------

def annuity_due(
    table: MortalityTable,
    age: int,
    rate: float,
    term: Optional[int] = None,
) -> float:
    """
    Annuity-due (ä) — present value of 1 paid at the *beginning* of each
    year the insured is alive.

    Parameters
    ----------
    table : MortalityTable
    age : int
        Age at valuation.
    rate : float
        Technical interest rate.
    term : int, optional
        Duration in years. If ``None``, whole-life annuity.

    Returns
    -------
    float
        Present value per unit of annual payment.
    """
    ct, age = _prepare(table, age, rate)
    if ct.Dx[age] == 0:
        return 0.0

    if term is None:
        return float(ct.Nx[age] / ct.Dx[age])
    else:
        term = _check_term(term)
        end_age = min(age + term, table.max_age + 1)
        if end_age > table.max_age:
            return float(ct.Nx[age] / ct.Dx[age])
        return float((ct.Nx[age] - ct.Nx[end_age]) / ct.Dx[age])


def annuity_immediate(
    table: MortalityTable,
    age: int,
    rate: float,
    term: Optional[int] = None,
) -> float:
    """
    Annuity-immediate (a) — present value of 1 paid at the *end* of each
    year the insured is alive.

    Relation: ax = äx − 1
    """
    return annuity_due(table, age, rate, term) - 1.0


# ---------------------------------------------------------------------------
# Insurance values
# ---------------------------------------------------------------------------

def whole_life_insurance(
    table: MortalityTable,
    age: int,
    rate: float,
) -> float:
    """
    Whole-life insurance (Ax) — present value of 1 paid at the end of the
    year of death.

    Parameters
    ----------
    table : MortalityTable
    age : int
    rate : float

    Returns
    -------
    float
    """
    ct, age = _prepare(table, age, rate)
    if ct.Dx[age] == 0:
        return 0.0
    return float(ct.Mx[age] / ct.Dx[age])


def term_insurance(
    table: MortalityTable,
    age: int,
    rate: float,
    term: int,
) -> float:
    """
    Term insurance — present value of 1 paid at end of year of death,
    only if death occurs within *term* years.

    Parameters
    ----------
    table : MortalityTable
    age : int
    rate : float
    term : int

    Returns
    -------
    float
    """
    ct, age = _prepare(table, age, rate)
    term = _check_term(term)
    if ct.Dx[age] == 0:
        return 0.0
    end_age = min(age + term, table.max_age + 1)
    if end_age > table.max_age:
        return float(ct.Mx[age] / ct.Dx[age])
    return float((ct.Mx[age] - ct.Mx[end_age]) / ct.Dx[age])


def pure_endowment(
    table: MortalityTable,
    age: int,
    rate: float,
    term: int,
) -> float:
    """
    Pure endowment — present value of 1 paid at the end of *term* years
    if the insured is still alive.

    Parameters
    ----------
    table : MortalityTable
    age : int
    rate : float
    term : int

    Returns
    -------
    float
    """
    ct, age = _prepare(table, age, rate)
    term = _check_term(term)
    if ct.Dx[age] == 0:
        return 0.0
    end_age = age + term
    if end_age > table.max_age:
        return 0.0
    return float(ct.Dx[end_age] / ct.Dx[age])


def endowment_insurance(
    table: MortalityTable,
    age: int,
    rate: float,
    term: int,
) -> float:
    """
    Endowment insurance (mixed) — term insurance + pure endowment.
    Pays 1 at end of year of death within *term* years, OR 1 at the end
    of *term* years if the insured survives.
    """
    return term_insurance(table, age, rate, term) + pure_endowment(
        table, age, rate, term
    )


# ---------------------------------------------------------------------------
# Premium calculation
# ---------------------------------------------------------------------------

def net_premium_whole_life(
    table: MortalityTable,
    age: int,
    rate: float,
) -> float:
    """
    Annual net level premium for a whole-life insurance of sum assured 1.

    P = Ax / äx
    """
    ad = annuity_due(table, age, rate)
    if ad == 0:
        return 0.0
    return whole_life_insurance(table, age, rate) / ad


def net_premium_term(
    table: MortalityTable,
    age: int,
    rate: float,
    term: int,
) -> float:
    """
    Annual net level premium for a term insurance of sum assured 1,
    payable during the term.

    P = A¹x:n⌉ / äx:n⌉
    """
    ad = annuity_due(table, age, rate, term=term)
    if ad == 0:
        return 0.0
    return term_insurance(table, age, rate, term) / ad


def net_premium_endowment(
    table: MortalityTable,
    age: int,
    rate: float,
    term: int,
) -> float:
    """
    Annual net level premium for an endowment insurance of sum assured 1.

    P = Ax:n⌉ / äx:n⌉
    """
    ad = annuity_due(table, age, rate, term=term)
    if ad == 0:
        return 0.0
    return endowment_insurance(table, age, rate, term) / ad


# ---------------------------------------------------------------------------
# Reserve (prospective)
# ---------------------------------------------------------------------------

def reserve_whole_life(
    table: MortalityTable,
    age_at_issue: int,
    rate: float,
    duration: int,
) -> float:
    """
    Prospective reserve at time *duration* for a whole-life insurance
    issued at *age_at_issue*.

    tVx = A(x+t) − P(x) · ä(x+t)
    """
    age_at_issue = table.check_age(age_at_issue)
    current_age = age_at_issue + _check_term(duration)
    if current_age > table.max_age:
        return 0.0
    premium = net_premium_whole_life(table, age_at_issue, rate)
    return (
        whole_life_insurance(table, current_age, rate)
        - premium * annuity_due(table, current_age, rate)
    )
