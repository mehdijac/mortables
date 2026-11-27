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

import datetime as _dt
from dataclasses import dataclass
from typing import Optional, Union

import numpy as np

from .core import MortalityTable, get_table


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


# ---------------------------------------------------------------------------
# Dates & exact age
# ---------------------------------------------------------------------------

def _to_date(value) -> _dt.date:
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    if isinstance(value, str):
        return _dt.date.fromisoformat(value)
    raise TypeError(f"Expected a date or an ISO string 'YYYY-MM-DD', got {value!r}")


def exact_age(birth_date, valuation_date, convention: str = "actual/365.25") -> float:
    """
    Age in years at *valuation_date* for someone born on *birth_date*.

    Parameters
    ----------
    birth_date, valuation_date : datetime.date or str (``"YYYY-MM-DD"``)
    convention : str
        ``"actual/365.25"`` (default): elapsed days / 365.25.
        ``"months"``: completed months / 12 (« âge en années et mois révolus »).
        ``"years"``: completed years (âge entier révolu).
    """
    b, v = _to_date(birth_date), _to_date(valuation_date)
    if v < b:
        raise ValueError("valuation_date must be on or after birth_date")
    if convention == "actual/365.25":
        return (v - b).days / 365.25
    months = (v.year - b.year) * 12 + (v.month - b.month) - (v.day < b.day)
    if convention == "months":
        return months / 12.0
    if convention == "years":
        return float(months // 12)
    raise ValueError(
        "convention must be 'actual/365.25', 'months' or 'years', "
        f"got {convention!r}"
    )


# ---------------------------------------------------------------------------
# General life annuity
# ---------------------------------------------------------------------------

def _resolve_table(table, birth_date, generation, label: str) -> MortalityTable:
    if isinstance(table, MortalityTable):
        return table
    if not isinstance(table, str):
        raise TypeError(f"{label} must be a table name or a MortalityTable")
    if generation is None and birth_date is not None:
        generation = _to_date(birth_date).year
    return get_table(table, generation=generation)


def _resolve_age(age, birth_date, valuation_date, convention, label: str) -> float:
    if age is not None:
        if birth_date is not None:
            raise ValueError(f"Give either {label} or a birth date, not both")
        return float(age)
    if birth_date is None or valuation_date is None:
        raise ValueError(f"{label} is required (or birth date + valuation_date)")
    return exact_age(birth_date, valuation_date, convention)


def annuity(
    table: Union[str, MortalityTable],
    age: Optional[float] = None,
    rate: float = 0.0,
    *,
    frequency: int = 1,
    timing: str = "advance",
    term: Optional[float] = None,
    deferred: float = 0.0,
    guaranteed: float = 0.0,
    reversion: float = 0.0,
    spouse_table: Union[str, MortalityTable, None] = None,
    spouse_age: Optional[float] = None,
    birth_date=None,
    spouse_birth_date=None,
    valuation_date=None,
    age_convention: str = "actual/365.25",
) -> float:
    """
    Present value of a life annuity of **1 per year**, paid in *frequency*
    instalments of ``1 / frequency``.

    Survival between integer ages uses linear interpolation of lx (UDD), so
    fractional ages and monthly/quarterly payments are valued exactly under
    that hypothesis (no Woolhouse approximation).

    Parameters
    ----------
    table : str or MortalityTable
        Annuitant's table.  With a generational table name (``"TGH05"``,
        ``"TGF05"``, ``"TGHF05"``) the generation is the year of *birth_date*.
    age : float, optional
        Age at valuation (may be fractional).  Alternatively give
        *birth_date* and *valuation_date*.
    rate : float
        Annual technical rate (may be negative, must be > -1).
    frequency : int
        Payments per year: 1 (annual), 2, 4 (quarterly), 12 (monthly)…
    timing : ``"advance"`` or ``"arrears"``
        Payment at the start (« terme à échoir ») or end (« terme échu ») of
        each period.
    term : float, optional
        Maximum payment period in years, counted from the first period
        (after deferral).  ``None``: for life.
    deferred : float
        Deferral in years before the first period starts (« rente différée »).
        Nothing is paid if the annuitant dies during the deferral.
    guaranteed : float
        Number of years, from the first period, during which instalments are
        paid whether or not the annuitant is alive (« annuités garanties »),
        provided they are alive at the end of the deferral.
    reversion : float
        Share of the annuity paid to the spouse after the annuitant's death
        (e.g. 0.6), while the spouse is alive.  Lives are independent.
    spouse_table, spouse_age, spouse_birth_date
        Spouse's table and age (or birth date), required if ``reversion > 0``.
    birth_date, valuation_date : date or ``"YYYY-MM-DD"``, optional
        Used to compute exact ages (see :func:`exact_age`).
    age_convention : str
        Convention for ages computed from dates (see :func:`exact_age`).

    Returns
    -------
    float

    Examples
    --------
    Monthly annuity in advance, 60 % reversion, valued on 31/12/2026:

    >>> annuity("TGH05", birth_date="1961-03-15", valuation_date="2026-12-31",
    ...         rate=0.02, frequency=12, reversion=0.6,
    ...         spouse_table="TGF05", spouse_birth_date="1963-07-02")  # doctest: +SKIP
    """
    rate = _check_rate(rate)
    m = frequency
    if isinstance(m, bool) or not float(m).is_integer() or m < 1:
        raise ValueError(f"frequency must be a positive integer, got {frequency!r}")
    m = int(m)
    if timing not in ("advance", "arrears"):
        raise ValueError(f"timing must be 'advance' or 'arrears', got {timing!r}")
    for label, value in (("deferred", deferred), ("guaranteed", guaranteed)):
        if value < 0:
            raise ValueError(f"{label} must be ≥ 0")
    if term is not None and term < 0:
        raise ValueError("term must be ≥ 0")
    if not 0.0 <= reversion <= 1.0:
        raise ValueError(f"reversion must be between 0 and 1, got {reversion}")

    tbl = _resolve_table(table, birth_date, None, "table")
    x = tbl.check_fractional_age(
        _resolve_age(age, birth_date, valuation_date, age_convention, "age")
    )

    spouse = None
    if reversion > 0:
        if spouse_table is None:
            raise ValueError("reversion > 0 requires spouse_table")
        spouse = _resolve_table(spouse_table, spouse_birth_date, None, "spouse_table")
        y = spouse.check_fractional_age(
            _resolve_age(spouse_age, spouse_birth_date, valuation_date,
                         age_convention, "spouse_age")
        )

    # Horizon: until every life involved is extinct
    horizon = tbl.max_age + 1 - x
    if spouse is not None:
        horizon = max(horizon, spouse.max_age + 1 - y)
    horizon = max(horizon - deferred, 0.0)
    if term is not None:
        horizon = min(horizon, float(term))
        if guaranteed > term:
            raise ValueError("guaranteed cannot exceed term")
    n = int(np.ceil(horizon * m - 1e-9))
    if n == 0:
        return 0.0

    j = np.arange(n, dtype=float)
    offset = 0.0 if timing == "advance" else 1.0
    t = deferred + (j + offset) / m           # payment times
    period_start = j / m                       # start of each period, after deferral

    sx = tbl.tpx(x, t)
    if spouse is not None:
        sy = spouse.tpx(y, t)
        prob = sx + reversion * sy * (1.0 - sx)
    else:
        prob = sx
    if guaranteed > 0:
        alive_at_start = tbl.tpx(x, deferred) if deferred > 0 else 1.0
        in_guarantee = period_start < guaranteed - 1e-12
        prob = np.where(in_guarantee, alive_at_start, prob)

    pv = np.sum(prob * (1.0 + rate) ** (-t)) / m
    return float(pv)
