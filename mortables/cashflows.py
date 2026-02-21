"""
Cash-flow projection for a portfolio of life annuities.

Given a list of annuitants (age, gender, annual rent), project the expected
payments year by year, together with the number of survivors and present
values.

Typical use-case: provisioning for a pension fund or an annuity book.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Union

import numpy as np

from .core import MortalityTable, get_table


def project(
    portfolio: Sequence[Dict],
    table: Union[str, MortalityTable] = "TF0002",
    years: int = 40,
    rate: float = 0.0,
    generation: Optional[int] = None,
) -> "pandas.DataFrame":
    """
    Project expected cash flows for a portfolio of annuitants.

    Parameters
    ----------
    portfolio : list of dict
        Each dict must contain:
        - ``age`` (int): current age of the annuitant
        - ``annual_rent`` (float): annual payment amount
        Optional:
        - ``gender`` (str): ``"M"`` or ``"F"`` (used if *table* is a string
          and you want gender-specific tables)
        - ``table`` (str): override the default table for this annuitant
    table : str or MortalityTable
        Default table to use (ignored if each annuitant has its own).
    years : int
        Projection horizon in years.
    rate : float
        Discount rate for present-value calculations.
    generation : int, optional
        Birth year (for generational tables).

    Returns
    -------
    pandas.DataFrame
        Columns: ``year``, ``expected_payment``, ``survivors``,
        ``pv_payment`` (present value at *rate*).

    Examples
    --------
    >>> from mortables.cashflows import project
    >>> pf = [
    ...     {"age": 65, "annual_rent": 12000},
    ...     {"age": 72, "annual_rent": 8000},
    ... ]
    >>> flows = project(pf, table="TF0002", years=30, rate=0.02)
    >>> flows.head()
    """
    import pandas as pd

    # Resolve default table once
    if isinstance(table, str):
        default_table = get_table(table, generation=generation)
    else:
        default_table = table

    # Pre-compute survival curves per annuitant
    records = []  # list of (rent, survival_probs_array)
    for person in portfolio:
        age = person["age"]
        rent = person["annual_rent"]

        # Determine which table to use for this person
        tbl = default_table
        if "table" in person:
            tbl = get_table(person["table"], generation=generation)

        # Build survival probabilities for each future year
        surv = np.ones(years + 1)
        for t in range(1, years + 1):
            current_age = age + t - 1
            if current_age > tbl.max_age:
                surv[t] = 0.0
            else:
                surv[t] = surv[t - 1] * (1.0 - tbl.qx_at(current_age))

        records.append((rent, surv))

    # Aggregate
    rows = []
    v = 1.0 / (1.0 + rate) if rate > 0 else 1.0
    for t in range(years + 1):
        total_payment = 0.0
        total_survivors = 0.0
        for rent, surv in records:
            total_payment += rent * surv[t]
            total_survivors += surv[t]
        pv = total_payment * (v ** t)
        rows.append(
            {
                "year": t,
                "expected_payment": round(total_payment, 2),
                "survivors": round(total_survivors, 4),
                "pv_payment": round(pv, 2),
            }
        )

    return pd.DataFrame(rows)


def total_provision(
    portfolio: Sequence[Dict],
    table: Union[str, MortalityTable] = "TF0002",
    years: int = 60,
    rate: float = 0.0,
    generation: Optional[int] = None,
) -> float:
    """
    Total provision (best estimate) = sum of all discounted expected payments.

    This is the simplest BEL (Best Estimate Liability) calculation for
    a book of annuities.

    Parameters
    ----------
    portfolio, table, years, rate, generation
        Same as :func:`project`.

    Returns
    -------
    float
        Total present value of expected future payments.
    """
    flows = project(portfolio, table=table, years=years, rate=rate, generation=generation)
    return float(flows["pv_payment"].sum())
