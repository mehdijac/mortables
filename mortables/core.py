"""
Core module — loading, accessing and manipulating mortality tables.

Two table types are supported:
  • **Period tables** (TH 00-02, TF 00-02): a single column of lx indexed by age.
  • **Generational tables** (TGH 05, TGF 05): lx depends on both age and birth
    year.  The official tables are stored as published (one lx column per
    generation 1900–2005); nothing is extrapolated or re-modelled.

In the official generational tables, a generation's lx column only starts at
the age reached in 1996 (radix 100 000 at that age).  Earlier ages are not
defined by the regulation: they are stored as ``NaN`` and any calculation
requested at such an age raises a ``ValueError``.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Where the data lives (inside the installed package)
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).parent / "tables"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _lx_to_qx(lx: np.ndarray) -> np.ndarray:
    """
    Derive qx from lx: ``qx = 1 − l(x+1) / l(x)``.

    The table is closed at the last age (``q_ω = 1``) and wherever ``lx = 0``.
    Ages where lx is undefined (``NaN``) get ``qx = NaN``.
    """
    lx = np.asarray(lx, dtype=float)
    qx = np.ones_like(lx)
    nxt = lx[1:]
    cur = lx[:-1]
    with np.errstate(divide="ignore", invalid="ignore"):
        q = 1.0 - np.where(cur > 0, nxt / cur, 0.0)
    qx[:-1] = q
    qx[np.isnan(lx)] = np.nan
    return qx


def _qx_to_lx(qx: np.ndarray, radix: float = 100_000.0) -> np.ndarray:
    """Convert qx to lx (float, no rounding) with a given radix."""
    qx = np.asarray(qx, dtype=float)
    lx = np.empty_like(qx)
    lx[0] = radix
    lx[1:] = radix * np.cumprod(1.0 - qx[:-1])
    return lx


def _as_age(age) -> int:
    """Validate that *age* is an integer (int or integral numpy scalar)."""
    if isinstance(age, (bool, np.bool_)):
        raise TypeError("age must be an integer")
    if isinstance(age, (int, np.integer)):
        return int(age)
    if isinstance(age, (float, np.floating)) and float(age).is_integer():
        return int(age)
    raise TypeError(
        f"age must be an integer, got {age!r} (fractional ages are not "
        "supported yet)"
    )


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class MortalityTable:
    """
    A mortality table indexed by integer age ``0 … max_age``.

    Attributes
    ----------
    name : str
        Short identifier, e.g. ``"TH0002"`` or ``"TGH05_1960"``.
    description : str
        Human-readable description.
    gender : str
        ``"M"`` (male), ``"F"`` (female) or ``"U"`` (unisex).
    table_type : str
        ``"period"`` or ``"generational"``.
    ages : np.ndarray
        Array of integer ages ``[0, 1, 2, …, max_age]``.
    qx : np.ndarray
        Probability of death at each age (``NaN`` where undefined, 1 at the
        last age).
    lx : np.ndarray
        Number of survivors at each age (float; ``NaN`` where undefined).
    generation : int or None
        Birth year, for generational tables only.
    metadata : dict
        Extra info (regulation reference, source, etc.).
    """

    name: str
    description: str
    gender: str
    table_type: str
    ages: np.ndarray
    qx: np.ndarray
    lx: np.ndarray
    generation: Optional[int] = None
    metadata: Dict = field(default_factory=dict)
    _cache: Dict = field(default_factory=dict, repr=False, compare=False)

    # -- Constructors ---------------------------------------------------------

    @classmethod
    def from_lx(cls, lx, name: str = "custom", gender: str = "U", **kwargs):
        """Build a table from an lx vector indexed by age 0, 1, 2, …"""
        lx = np.asarray(lx, dtype=float)
        return cls(
            name=name,
            description=kwargs.pop("description", name),
            gender=gender,
            table_type=kwargs.pop("table_type", "period"),
            ages=np.arange(len(lx)),
            qx=_lx_to_qx(lx),
            lx=lx,
            **kwargs,
        )

    @classmethod
    def from_qx(cls, qx, name: str = "custom", gender: str = "U",
                radix: float = 100_000.0, **kwargs):
        """Build a table from a qx vector indexed by age 0, 1, 2, …"""
        qx = np.asarray(qx, dtype=float)
        return cls(
            name=name,
            description=kwargs.pop("description", name),
            gender=gender,
            table_type=kwargs.pop("table_type", "period"),
            ages=np.arange(len(qx)),
            qx=qx,
            lx=_qx_to_lx(qx, radix),
            **kwargs,
        )

    # -- Derived quantities --------------------------------------------------

    @property
    def max_age(self) -> int:
        return int(self.ages[-1])

    @property
    def min_age(self) -> int:
        """First age at which the table is defined (0 for period tables)."""
        defined = np.flatnonzero(~np.isnan(self.lx))
        return int(defined[0]) if defined.size else self.max_age + 1

    @property
    def px(self) -> np.ndarray:
        """Probability of surviving the year: px = 1 − qx."""
        return 1.0 - self.qx

    @property
    def dx(self) -> np.ndarray:
        """Expected deaths between age x and x+1."""
        return self.lx * self.qx

    @property
    def ex(self) -> np.ndarray:
        """Curtate life expectancy at each age: ``Σ_{k≥1} l(x+k) / l(x)``."""
        lx = np.nan_to_num(self.lx, nan=0.0)
        tail = np.concatenate([np.cumsum(lx[::-1])[::-1][1:], [0.0]])
        with np.errstate(divide="ignore", invalid="ignore"):
            ex = np.where(lx > 0, tail / np.where(lx > 0, lx, 1.0), 0.0)
        ex[np.isnan(self.lx)] = np.nan
        return ex

    # -- Validation ------------------------------------------------------------

    def check_age(self, age) -> int:
        """
        Return *age* as an int, or raise if it is not an integer within
        ``[min_age, max_age]``.
        """
        age = _as_age(age)
        if age < 0 or age > self.max_age:
            raise ValueError(f"Age {age} is out of range [0, {self.max_age}]")
        if np.isnan(self.lx[age]):
            raise ValueError(
                f"Age {age} is not defined in table '{self.name}' "
                f"(first defined age: {self.min_age})"
            )
        return age

    # -- Convenience methods -------------------------------------------------

    def qx_at(self, age: int) -> float:
        """Return qx at a given age."""
        return float(self.qx[self.check_age(age)])

    def survival_probability(self, from_age: int, to_age: int) -> float:
        """Probability of surviving from *from_age* to *to_age*."""
        from_age = self.check_age(from_age)
        to_age = _as_age(to_age)
        if from_age > to_age:
            raise ValueError("from_age must be ≤ to_age")
        if to_age > self.max_age:
            return 0.0
        return float(self.lx[to_age] / self.lx[from_age]) if self.lx[from_age] else 0.0

    def life_expectancy(self, age: int = 0) -> float:
        """Curtate life expectancy at *age*."""
        return float(self.ex[self.check_age(age)])

    # -- Fractional ages (linear interpolation of lx, i.e. UDD) ---------------

    def check_fractional_age(self, age: float) -> float:
        """Validate a (possibly fractional) age within ``[min_age, max_age + 1]``."""
        if isinstance(age, (bool, np.bool_)):
            raise TypeError("age must be a number")
        age = float(age)
        if not np.isfinite(age) or age < self.min_age or age > self.max_age + 1:
            raise ValueError(
                f"Age {age} is out of range [{self.min_age}, {self.max_age + 1}] "
                f"for table '{self.name}'"
            )
        return age

    def lx_at(self, x):
        """
        lx at (possibly fractional) age(s) *x*, by **linear interpolation**
        between integer ages (uniform distribution of deaths, the usual
        convention in France).  ``l(max_age + 1) = 0``; beyond, 0.
        """
        x = np.asarray(x, dtype=float)
        start = self.min_age
        nodes = np.arange(start, self.max_age + 2, dtype=float)
        values = np.append(self.lx[start:], 0.0)
        out = np.interp(x, nodes, values, right=0.0)
        out = np.where(x < start, np.nan, out)
        return float(out) if out.ndim == 0 else out

    def tpx(self, age: float, t):
        """Probability that a life aged *age* survives *t* more years (t ≥ 0)."""
        age = self.check_fractional_age(age)
        l0 = self.lx_at(age)
        if l0 <= 0:
            return 0.0 if np.ndim(t) == 0 else np.zeros(np.shape(t))
        return self.lx_at(age + np.asarray(t, dtype=float)) / l0

    # -- Adjusted tables -------------------------------------------------------

    def _with_qx(self, qx: np.ndarray, name: str, description: str,
                 adjustment: Dict) -> "MortalityTable":
        """New table with the same layout, lx rebuilt from *qx* (radix kept)."""
        qx = np.asarray(qx, dtype=float).copy()
        qx[-1] = 1.0
        lx = np.full_like(qx, np.nan)
        defined = np.flatnonzero(~np.isnan(qx))
        if defined.size:
            start = int(defined[0])
            radix = self.lx[start] if not np.isnan(self.lx[start]) else 100_000.0
            lx[start] = radix
            lx[start + 1:] = radix * np.cumprod(1.0 - qx[start:-1])
        meta = dict(self.metadata)
        meta["adjustments"] = list(meta.get("adjustments", [])) + [adjustment]
        return MortalityTable(
            name=name,
            description=description,
            gender=self.gender,
            table_type=self.table_type,
            ages=self.ages.copy(),
            qx=qx,
            lx=lx,
            generation=self.generation,
            metadata=meta,
        )

    def age_shifted(self, years: int) -> "MortalityTable":
        """
        Age shift (« décalage d'âge »): ``q'(x) = q(x + years)``.

        ``years > 0`` ages the insured (more mortality), ``years < 0`` makes
        them younger (less mortality, more prudent for annuities).  Ages that
        fall outside the table get ``q = 1`` (beyond the end) or are left
        undefined (before the start).
        """
        k = _as_age(years)
        qx = np.full_like(self.qx, np.nan)
        n = len(self.qx)
        for x in range(n):
            src = x + k
            if src >= n:
                qx[x] = 1.0
            elif src >= 0:
                qx[x] = self.qx[src]
        if k < 0:  # first ages map before the table start: undefined
            qx[: max(0, self.min_age - k)] = np.nan
        return self._with_qx(
            qx,
            name=f"{self.name}{k:+d}a",
            description=f"{self.description} — décalage d'âge {k:+d} an(s)",
            adjustment={"type": "age_shift", "years": k},
        )

    def scaled(self, factor: float) -> "MortalityTable":
        """
        Multiply every qx by *factor* (capped at 1): abatement (``factor < 1``)
        or loading (``factor > 1``).  E.g. Solvency II longevity shock:
        ``scaled(0.80)``; mortality shock: ``scaled(1.15)``.
        """
        factor = float(factor)
        if not factor >= 0:
            raise ValueError(f"factor must be ≥ 0, got {factor}")
        qx = np.minimum(self.qx * factor, 1.0)
        return self._with_qx(
            qx,
            name=f"{self.name}x{factor:g}",
            description=f"{self.description} — qx × {factor:g}",
            adjustment={"type": "scale", "factor": factor},
        )

    def __repr__(self) -> str:
        gen = f", generation={self.generation}" if self.generation else ""
        return (
            f"MortalityTable(name='{self.name}', gender='{self.gender}', "
            f"max_age={self.max_age}{gen})"
        )

    def to_dataframe(self):
        """Return a pandas DataFrame with columns age, lx, qx, px, dx, ex."""
        import pandas as pd

        return pd.DataFrame(
            {
                "age": self.ages,
                "lx": self.lx,
                "qx": self.qx,
                "px": self.px,
                "dx": self.dx,
                "ex": self.ex,
            }
        )


# ---------------------------------------------------------------------------
# Internal loaders (cached: files are read once per process)
# ---------------------------------------------------------------------------
def _parse(value: str) -> float:
    return float(value) if value.strip() != "" else np.nan


@lru_cache(maxsize=None)
def _load_period_csv(filepath: Path) -> Tuple[np.ndarray, np.ndarray]:
    """Read a period table CSV (columns ``age, lx``) → (ages, lx)."""
    ages, lx = [], []
    with open(filepath, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ages.append(int(row["age"]))
            lx.append(_parse(row["lx"]))
    return np.array(ages), np.array(lx, dtype=float)


@lru_cache(maxsize=None)
def _load_generational_csv(filepath: Path) -> Tuple[np.ndarray, Dict[int, np.ndarray]]:
    """Read a wide generational CSV (``age, <gen1>, <gen2>, …``)."""
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        gens = [int(g) for g in header[1:]]
        rows = list(reader)
    ages = np.array([int(r[0]) for r in rows])
    by_gen = {
        g: np.array([_parse(r[j]) for r in rows], dtype=float)
        for j, g in enumerate(gens, start=1)
    }
    return ages, by_gen


# ---------------------------------------------------------------------------
# Catalogue (lazy-loaded)
# ---------------------------------------------------------------------------
_CATALOGUE: Optional[dict] = None

_ALIASES = {
    "TH00-02": "TH0002",
    "TF00-02": "TF0002",
    "TH-00-02": "TH0002",
    "TF-00-02": "TF0002",
    "TH": "TH0002",
    "TF": "TF0002",
    "TGH2005": "TGH05",
    "TGF2005": "TGF05",
    "TGHF2005": "TGHF05",
    "TGHF": "TGHF05",
}


def _load_catalogue() -> dict:
    global _CATALOGUE
    if _CATALOGUE is not None:
        return _CATALOGUE

    catalogue = {}
    for tables_json in sorted(_DATA_DIR.rglob("TABLES.json")):
        with open(tables_json, encoding="utf-8") as f:
            info = json.load(f)
        country = info.get("country", "Unknown")
        for tbl in info["tables"]:
            tbl["_country"] = country
            tbl["_dir"] = tables_json.parent
            catalogue[tbl["id"]] = tbl
    _CATALOGUE = catalogue
    return _CATALOGUE


def _normalise_id(table_id: str) -> str:
    key = table_id.upper().replace(" ", "")
    return _ALIASES.get(key, key)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_tables() -> List[Dict]:
    """
    List all available mortality tables.

    Returns
    -------
    list of dict
        Each dict contains ``id``, ``name``, ``description``, ``type``,
        ``gender``, ``regulation``, ``usage``, ``file`` and ``source``.

    Examples
    --------
    >>> from mortables import list_tables
    >>> for t in list_tables():
    ...     print(t["id"], "-", t["name"])
    TH0002 - TH 00-02
    TF0002 - TF 00-02
    TGH05 - TGH 05
    TGF05 - TGF 05
    """
    cat = _load_catalogue()
    return [
        {k: v for k, v in entry.items() if not k.startswith("_")}
        for entry in cat.values()
    ]


def get_table(
    table_id: str,
    generation: Optional[int] = None,
) -> MortalityTable:
    """
    Load a mortality table by its identifier.

    Parameters
    ----------
    table_id : str
        Table identifier.  Accepted values:
        ``"TH0002"``, ``"TF0002"``, ``"TGH05"``, ``"TGF05"``.
        Common aliases are also supported: ``"TH00-02"`` → ``"TH0002"``, etc.
    generation : int, optional
        Birth year (required for generational tables TGH05/TGF05,
        ignored for period tables).

    Returns
    -------
    MortalityTable

    Raises
    ------
    ValueError
        If *table_id* is unknown or *generation* is missing/out of range for
        a generational table.

    Examples
    --------
    >>> from mortables import get_table
    >>> th = get_table("TH0002")
    >>> th.lx[60]
    85538.0
    >>> round(th.life_expectancy(0), 5)
    75.00752

    >>> tg = get_table("TGH05", generation=1950)
    >>> tg.lx[60]
    96430.0
    """
    table_id = _normalise_id(table_id)

    cat = _load_catalogue()
    if table_id not in cat:
        available = ", ".join(sorted(cat.keys()))
        raise ValueError(
            f"Unknown table '{table_id}'. Available tables: {available}"
        )

    entry = cat[table_id]
    filepath = entry["_dir"] / entry["file"]
    metadata = {
        "regulation": entry.get("regulation", ""),
        "usage": entry.get("usage", ""),
        "country": entry.get("_country", ""),
        "source": entry.get("source", ""),
    }

    if entry["type"] == "period":
        ages, lx = _load_period_csv(filepath)
        lx = lx.copy()
        return MortalityTable(
            name=entry["id"],
            description=entry["description"],
            gender=entry["gender"],
            table_type="period",
            ages=ages.copy(),
            qx=_lx_to_qx(lx),
            lx=lx,
            metadata=metadata,
        )

    if entry["type"] == "generational":
        ages, by_gen = _load_generational_csv(filepath)
        min_gen, max_gen = min(by_gen), max(by_gen)
        if generation is None:
            raise ValueError(
                f"Table '{table_id}' is generational: you must provide a "
                f"'generation' (birth year between {min_gen} and {max_gen})."
            )
        generation = _as_age(generation)
        if generation not in by_gen:
            raise ValueError(
                f"Generation {generation} out of range [{min_gen}, {max_gen}]"
            )
        lx = by_gen[generation].copy()
        return MortalityTable(
            name=f"{entry['id']}_{generation}",
            description=f"{entry['description']} — génération {generation}",
            gender=entry["gender"],
            table_type="generational",
            ages=ages.copy(),
            qx=_lx_to_qx(lx),
            lx=lx,
            generation=generation,
            metadata=metadata,
        )

    raise ValueError(f"Unsupported table type: {entry['type']}")
