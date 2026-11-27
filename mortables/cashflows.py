"""
Cash-flow projection for a portfolio of life annuities.

Given a list of annuitants (age, annual rent, and optionally table, gender
and birth year), project the expected payments year by year, together with
the expected number of survivors and present values.

Conventions
-----------
* Rents are paid annually **in advance** (at times t = 0, 1, 2, …) as long
  as the annuitant is alive: the result is consistent with
  :func:`mortables.life.annuity_due`.
* With a generational table (TGH05/TGF05), each annuitant is valued with
  their own generation (``generation`` / ``birth_year`` key), falling back
  to the function's ``generation`` argument.

Typical use-case: provisioning for a pension fund or an annuity book.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

if TYPE_CHECKING:  # pragma: no cover
    import pandas

from .core import MortalityTable, _normalise_id, get_table

# Gender counterparts of the regulatory tables
_GENDER_PAIRS = {
    ("TH0002", "F"): "TF0002",
    ("TF0002", "M"): "TH0002",
    ("TGH05", "F"): "TGF05",
    ("TGF05", "M"): "TGH05",
}


def _resolve_person_table(
    person: Dict,
    default: Union[str, MortalityTable],
    generation: Optional[int],
    cache: Dict[Tuple[str, Optional[int]], MortalityTable],
) -> MortalityTable:
    gender = person.get("gender")
    if gender is not None:
        gender = str(gender).upper()
        if gender not in ("M", "F"):
            raise ValueError(f"gender must be 'M' or 'F', got {person['gender']!r}")

    spec = person.get("table", default)
    if isinstance(spec, MortalityTable):
        if gender and spec.gender in ("M", "F") and spec.gender != gender:
            raise ValueError(
                f"Annuitant has gender '{gender}' but table '{spec.name}' is "
                f"gender '{spec.gender}'. Pass a table name or set 'table'."
            )
        return spec

    table_id = _normalise_id(spec)
    if gender and "table" not in person:
        table_id = _GENDER_PAIRS.get((table_id, gender), table_id)

    gen = person.get("generation", person.get("birth_year", generation))
    key = (table_id, gen)
    if key not in cache:
        tbl = get_table(table_id, generation=gen)
        # period tables ignore the generation: share one instance
        cache[key] = tbl
    return cache[key]


def _survival_matrix(
    portfolio: Sequence[Dict],
    table: Union[str, MortalityTable],
    years: Optional[int],
    generation: Optional[int],
) -> Tuple[np.ndarray, np.ndarray]:
    """Return (rents, survival) with survival[i, t] = P(annuitant i alive at t)."""
    cache: Dict = {}
    resolved: List[Tuple[float, int, MortalityTable]] = []
    for i, person in enumerate(portfolio):
        if "age" not in person or "annual_rent" not in person:
            raise ValueError(f"Annuitant #{i} must have 'age' and 'annual_rent'")
        tbl = _resolve_person_table(person, table, generation, cache)
        age = tbl.check_age(person["age"])
        resolved.append((float(person["annual_rent"]), age, tbl))

    if years is None:
        years = max((t.max_age - a for _, a, t in resolved), default=0)
    if years < 0:
        raise ValueError("years must be ≥ 0")

    rents = np.array([r for r, _, _ in resolved], dtype=float)
    surv = np.zeros((len(resolved), years + 1))
    for i, (_, age, tbl) in enumerate(resolved):
        n = min(years, tbl.max_age - age) + 1
        lx = tbl.lx[age:age + n]
        surv[i, :n] = lx / lx[0] if lx[0] > 0 else 0.0
    return rents, surv


def project(
    portfolio: Sequence[Dict],
    table: Union[str, MortalityTable] = "TF0002",
    years: Optional[int] = None,
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

        - ``table`` (str or MortalityTable): table for this annuitant
        - ``gender`` (``"M"`` / ``"F"``): when ``table`` is not given and the
          default table is a regulatory one, picks its gender counterpart
          (TH0002 ↔ TF0002, TGH05 ↔ TGF05)
        - ``generation`` or ``birth_year`` (int): birth year, for
          generational tables
    table : str or MortalityTable
        Default table.
    years : int, optional
        Projection horizon in years. ``None`` (default) projects until the
        end of the table for every annuitant (full run-off).
    rate : float
        Annual discount rate (may be negative, must be > -1).
    generation : int, optional
        Default birth year for generational tables.

    Returns
    -------
    pandas.DataFrame
        Columns: ``year``, ``expected_payment``, ``survivors``,
        ``discount_factor``, ``pv_payment``. Values are not rounded.

    Examples
    --------
    >>> from mortables.cashflows import project
    >>> pf = [
    ...     {"age": 65, "annual_rent": 12000, "gender": "M", "birth_year": 1960},
    ...     {"age": 72, "annual_rent": 8000, "gender": "F", "birth_year": 1953},
    ... ]
    >>> flows = project(pf, table="TGH05", rate=0.02)
    """
    import pandas as pd

    rate = float(rate)
    if not rate > -1.0:
        raise ValueError(f"rate must be > -1, got {rate}")

    rents, surv = _survival_matrix(portfolio, table, years, generation)
    t = np.arange(surv.shape[1])
    discount = (1.0 + rate) ** -t.astype(float)
    expected = rents @ surv
    return pd.DataFrame(
        {
            "year": t,
            "expected_payment": expected,
            "survivors": surv.sum(axis=0),
            "discount_factor": discount,
            "pv_payment": expected * discount,
        }
    )


def total_provision(
    portfolio: Sequence[Dict],
    table: Union[str, MortalityTable] = "TF0002",
    years: Optional[int] = None,
    rate: float = 0.0,
    generation: Optional[int] = None,
) -> float:
    """
    Total provision (best estimate) = sum of all discounted expected payments.

    With the default ``years=None`` (full run-off), the result equals
    ``Σ rent × ä(age)`` computed with :func:`mortables.life.annuity_due`.

    Parameters
    ----------
    portfolio, table, years, rate, generation
        Same as :func:`project`.

    Returns
    -------
    float
        Total present value of expected future payments.
    """
    flows = project(
        portfolio, table=table, years=years, rate=rate, generation=generation
    )
    return float(flows["pv_payment"].sum())
