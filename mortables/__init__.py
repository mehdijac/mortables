"""
mortables — French regulatory mortality tables & actuarial functions.

Quick start::

    from mortables import get_table, list_tables, life

    # Load a table
    th = get_table("TH0002")
    print(th.life_expectancy(65))

    # Generational table (official lx, one column per birth year)
    tg = get_table("TGH05", generation=1960)

    # Actuarial calculations
    print(life.annuity_due(th, age=65, rate=0.02))
"""

from . import cashflows, life, viz
from .core import MortalityTable, get_table, list_tables

__version__ = "0.2.0"
__all__ = [
    "MortalityTable",
    "get_table",
    "list_tables",
    "life",
    "cashflows",
    "viz",
]
