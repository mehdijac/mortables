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


def commutation(table: MortalityTable, rate: float) -> CommutationTable:
    """
    Compute the full set of commutation numbers.

    Parameters
    ----------
    table : MortalityTable
    rate : float
        Annual technical interest rate (e.g. 0.02 for 2 %).

    Returns
    -------
    CommutationTable
    """
    v = 1.0 / (1.0 + rate)  # discount factor
    n = len(table.ages)

    # Dx = lx · v^x
    Dx = table.lx.astype(float) * (v ** table.ages.astype(float))

    # Cx = dx · v^(x+1)  where dx = lx · qx
    dx = table.lx.astype(float) * table.qx
    Cx = dx * (v ** (table.ages.astype(float) + 1))

    # Nx = sum of Dx from age x to omega
    Nx = np.flip(np.cumsum(np.flip(Dx)))

    # Sx = sum of Nx from age x to omega
    Sx = np.flip(np.cumsum(np.flip(Nx)))

    # Mx = sum of Cx from age x to omega
    Mx = np.flip(np.cumsum(np.flip(Cx)))

    # Rx = sum of Mx from age x to omega
    Rx = np.flip(np.cumsum(np.flip(Mx)))

    return CommutationTable(
        Dx=Dx, Nx=Nx, Sx=Sx, Cx=Cx, Mx=Mx, Rx=Rx,
        rate=rate, table_name=table.name,
    )


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
    ct = commutation(table, rate)
    if ct.Dx[age] == 0:
        return 0.0

    if term is None:
        return ct.Nx[age] / ct.Dx[age]
    else:
        end_age = min(age + term, table.max_age + 1)
        if end_age > table.max_age:
            return ct.Nx[age] / ct.Dx[age]
        return (ct.Nx[age] - ct.Nx[end_age]) / ct.Dx[age]


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
    ct = commutation(table, rate)
    if ct.Dx[age] == 0:
        return 0.0
    return ct.Mx[age] / ct.Dx[age]


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
    ct = commutation(table, rate)
    if ct.Dx[age] == 0:
        return 0.0
    end_age = min(age + term, table.max_age + 1)
    if end_age > table.max_age:
        return ct.Mx[age] / ct.Dx[age]
    return (ct.Mx[age] - ct.Mx[end_age]) / ct.Dx[age]


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
    ct = commutation(table, rate)
    if ct.Dx[age] == 0:
        return 0.0
    end_age = age + term
    if end_age > table.max_age:
        return 0.0
    return ct.Dx[end_age] / ct.Dx[age]


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
    current_age = age_at_issue + duration
    if current_age > table.max_age:
        return 0.0
    premium = net_premium_whole_life(table, age_at_issue, rate)
    return (
        whole_life_insurance(table, current_age, rate)
        - premium * annuity_due(table, current_age, rate)
    )
