"""
Core module — loading, accessing and manipulating mortality tables.

Two table types are supported:
  • **Period tables** (TH 00-02, TF 00-02): a single column of qx indexed by age.
  • **Generational tables** (TGH 05, TGF 05): qx depends on both age and birth year.
    Stored as a base qx vector + annual improvement rates; any generation between
    1900 and 2005 can be derived on the fly.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np

# ---------------------------------------------------------------------------
# Where the data lives (inside the installed package)
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).parent / "tables"
_FR_DIR = _DATA_DIR / "france"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class MortalityTable:
    """
    A mortality table: a vector of qx (probability of death within one year)
    indexed by integer age.

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
        Probability of death at each age.
    lx : np.ndarray
        Number of survivors at each age (radix = 100 000).
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

    # -- Derived quantities --------------------------------------------------

    @property
    def max_age(self) -> int:
        return int(self.ages[-1])

    @property
    def px(self) -> np.ndarray:
        """Probability of surviving the year: px = 1 − qx."""
        return 1.0 - self.qx

    @property
    def dx(self) -> np.ndarray:
        """Expected deaths between age x and x+1 (for radix 100 000)."""
        return self.lx * self.qx

    @property
    def ex(self) -> np.ndarray:
        """Curtate life expectancy at each age."""
        n = len(self.lx)
        ex = np.zeros(n)
        for i in range(n):
            if self.lx[i] == 0:
                ex[i] = 0.0
            else:
                ex[i] = np.sum(self.lx[i + 1:]) / self.lx[i]
        return ex

    # -- Convenience methods -------------------------------------------------

    def qx_at(self, age: int) -> float:
        """Return qx at a given age."""
        if age < 0 or age > self.max_age:
            raise ValueError(f"Age {age} is out of range [0, {self.max_age}]")
        return float(self.qx[age])

    def survival_probability(self, from_age: int, to_age: int) -> float:
        """Probability of surviving from *from_age* to *to_age*."""
        if from_age > to_age:
            raise ValueError("from_age must be ≤ to_age")
        return float(np.prod(self.px[from_age:to_age]))

    def life_expectancy(self, age: int = 0) -> float:
        """Curtate life expectancy at *age*."""
        return float(self.ex[age])

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
# Internal loaders
# ---------------------------------------------------------------------------
def _load_period_csv(filepath: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Read a period table CSV → (ages, lx, qx)."""
    ages, lx, qx = [], [], []
    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ages.append(int(row["age"]))
            lx.append(float(row["lx"]))
            qx.append(float(row["qx"]))
    return np.array(ages), np.array(lx), np.array(qx)


def _load_generational_json(filepath: Path) -> dict:
    """Read a generational table JSON (base_qx + improvement rates)."""
    with open(filepath) as f:
        return json.load(f)


def _derive_generation_qx(
    base_qx: Sequence[float],
    improvements: Sequence[float],
    base_gen: int,
    target_gen: int,
) -> np.ndarray:
    """
    Derive qx for a specific generation from the base table.

    Formula:  qx(gen, age) = base_qx(age) × exp(−improvement(age) × (gen − base_gen))

    Later generations have lower mortality (positive improvements → lower qx).
    """
    shift = target_gen - base_gen
    qx = np.array(
        [
            min(bq * math.exp(-imp * shift), 1.0)
            for bq, imp in zip(base_qx, improvements)
        ]
    )
    return np.clip(qx, 0.0, 1.0)


def _qx_to_lx(qx: np.ndarray, radix: int = 100_000) -> np.ndarray:
    """Convert qx to lx with a given radix."""
    n = len(qx)
    lx = np.zeros(n)
    lx[0] = radix
    for i in range(1, n):
        lx[i] = lx[i - 1] * (1 - qx[i - 1])
    return np.round(lx).astype(int)


# ---------------------------------------------------------------------------
# Catalogue (lazy-loaded)
# ---------------------------------------------------------------------------
_CATALOGUE: Optional[dict] = None


def _load_catalogue() -> dict:
    global _CATALOGUE
    if _CATALOGUE is not None:
        return _CATALOGUE

    _CATALOGUE = {}
    for tables_json in _DATA_DIR.rglob("TABLES.json"):
        with open(tables_json) as f:
            info = json.load(f)
        country = info.get("country", "Unknown")
        for tbl in info["tables"]:
            tbl["_country"] = country
            tbl["_dir"] = tables_json.parent
            _CATALOGUE[tbl["id"]] = tbl
    return _CATALOGUE


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
        ``gender``, and ``regulation``.

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
        Birth year (required for generational tables TGH05/TGF05).

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
    >>> th.qx_at(65)
    0.02304736
    >>> th.life_expectancy(0)
    75.8...

    >>> tg = get_table("TGH05", generation=1960)
    >>> tg.life_expectancy(65)
    22.1...
    """
    # Normalise aliases
    aliases = {
        "TH00-02": "TH0002",
        "TF00-02": "TF0002",
        "TH-00-02": "TH0002",
        "TF-00-02": "TF0002",
        "TH": "TH0002",
        "TF": "TF0002",
    }
    table_id = aliases.get(table_id.upper().replace(" ", ""), table_id.upper().replace(" ", ""))

    cat = _load_catalogue()
    if table_id not in cat:
        available = ", ".join(sorted(cat.keys()))
        raise ValueError(
            f"Unknown table '{table_id}'. Available tables: {available}"
        )

    entry = cat[table_id]
    filepath = entry["_dir"] / entry["file"]

    if entry["type"] == "period":
        ages, lx, qx = _load_period_csv(filepath)
        return MortalityTable(
            name=entry["id"],
            description=entry["description"],
            gender=entry["gender"],
            table_type="period",
            ages=ages,
            qx=qx,
            lx=lx,
            metadata={
                "regulation": entry.get("regulation", ""),
                "usage": entry.get("usage", ""),
                "country": entry.get("_country", ""),
            },
        )

    elif entry["type"] == "generational":
        if generation is None:
            raise ValueError(
                f"Table '{table_id}' is generational: you must provide a "
                f"'generation' (birth year between 1900 and 2005)."
            )
        data = _load_generational_json(filepath)
        min_gen = data["min_generation"]
        max_gen = data["max_generation"]
        if not (min_gen <= generation <= max_gen):
            raise ValueError(
                f"Generation {generation} out of range [{min_gen}, {max_gen}]"
            )

        qx = _derive_generation_qx(
            data["base_qx"],
            data["annual_improvement"],
            data["base_generation"],
            generation,
        )
        ages = np.arange(len(qx))
        lx = _qx_to_lx(qx)

        return MortalityTable(
            name=f"{entry['id']}_{generation}",
            description=f"{entry['description']} — génération {generation}",
            gender=entry["gender"],
            table_type="generational",
            ages=ages,
            qx=qx,
            lx=lx,
            generation=generation,
            metadata={
                "regulation": entry.get("regulation", ""),
                "usage": entry.get("usage", ""),
                "country": entry.get("_country", ""),
                "base_generation": data["base_generation"],
            },
        )

    else:
        raise ValueError(f"Unsupported table type: {entry['type']}")
