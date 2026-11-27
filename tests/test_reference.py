"""
Reference tests: values taken from the official Lx files (ISFA,
ressources-actuarielles.net: TH00-02_D.xls, TF00-02_D.xls, TGHF05.xls).

l60 for generation 1950 (TGH05: 96 430, TGF05: 97 222) is also
corroborated by an independent publication (moneyvox.fr).

If one of these tests fails, the embedded data no longer matches the
regulatory tables: do NOT relax the test, fix the data.
"""

import hashlib
from pathlib import Path

import pytest

from mortables import get_table

DATA = Path(__file__).resolve().parent.parent / "mortables" / "tables" / "france"

SHA256 = {
    "TH0002.csv": "64b5aabd298151d73298c128a212da324c89da5f8e8d87afde150a26bf739a99",
    "TF0002.csv": "f071bd8e28543a5191960daa3e9dfcd4d37a37ad65795cff495abd6087f734f4",
    "TGH05.csv": "9a197fd3979d143269a7dd3f11bfe7034d881ec1920119a6ec3f634d42a90362",
    "TGF05.csv": "919631ed82d4de0123eb0222bc766d13072ac3b4ee20cdba96479ce62ae596a7",
    "TGHF05.csv": "d1eb943fb3397dcb1d6683c60ce690f962d7098ac2ec24824a86c56169216fca",
}


@pytest.mark.parametrize("filename,digest", sorted(SHA256.items()))
def test_data_files_unchanged(filename, digest):
    assert hashlib.sha256((DATA / filename).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize(
    "table_id,age,lx",
    [
        ("TH0002", 0, 100000),
        ("TH0002", 1, 99511),
        ("TH0002", 2, 99473),
        ("TH0002", 60, 85538),
        ("TH0002", 65, 79926),
        ("TH0002", 99, 1032),
        ("TH0002", 109, 2),
        ("TF0002", 1, 99616),
        ("TF0002", 60, 93329),
        ("TF0002", 65, 90797),
        ("TF0002", 99, 4516),
    ],
)
def test_period_lx(table_id, age, lx):
    assert get_table(table_id).lx[age] == lx


@pytest.mark.parametrize(
    "table_id,age,ex",
    [
        # "Ex" column of the official files (curtate life expectancy)
        ("TH0002", 0, 75.00752),
        ("TH0002", 60, 20.13638382940915),
        ("TH0002", 65, 16.40045792357931),
        ("TF0002", 0, 82.48837),
        ("TF0002", 60, 25.27843435588081),
        ("TF0002", 65, 20.92351068867914),
    ],
)
def test_period_life_expectancy(table_id, age, ex):
    assert get_table(table_id).life_expectancy(age) == pytest.approx(ex, abs=1e-6)


@pytest.mark.parametrize(
    "table_id,generation,age,lx",
    [
        ("TGH05", 1950, 46, 100000),
        ("TGH05", 1950, 60, 96430),
        ("TGH05", 1950, 65, 94306),
        ("TGH05", 1960, 60, 96391),
        ("TGH05", 1960, 65, 94702),
        ("TGH05", 2005, 0, 100000),
        ("TGH05", 2005, 60, 97751),
        ("TGH05", 2005, 65, 97144),
        ("TGF05", 1950, 60, 97222),
        ("TGF05", 1950, 65, 95696),
        ("TGF05", 1960, 60, 96833),
        ("TGF05", 1960, 65, 95488),
        ("TGF05", 2005, 60, 97083),
        ("TGF05", 2005, 65, 96454),
    ],
)
def test_generational_lx(table_id, generation, age, lx):
    assert get_table(table_id, generation=generation).lx[age] == lx


@pytest.mark.parametrize(
    "generation,min_age", [(1900, 96), (1950, 46), (1996, 0), (2005, 0)]
)
def test_generational_first_defined_age(generation, min_age):
    """Each generation starts at the age reached in 1996 (radix 100 000)."""
    tg = get_table("TGH05", generation=generation)
    assert tg.min_age == min_age
    assert tg.lx[min_age] == 100000


def test_generational_undefined_ages_raise():
    tg = get_table("TGH05", generation=1950)
    with pytest.raises(ValueError, match="not defined"):
        tg.qx_at(30)
    with pytest.raises(ValueError, match="not defined"):
        tg.life_expectancy(0)


def test_generational_tables_more_prudent_for_annuities():
    """TGH/TGF 05 are annuity tables: longer lives than the period tables."""
    for gen_id, period_id in (("TGH05", "TH0002"), ("TGF05", "TF0002")):
        for generation in (1940, 1950, 1960, 1980):
            tg = get_table(gen_id, generation=generation)
            assert tg.life_expectancy(65) > get_table(period_id).life_expectancy(65)


def test_tghf05_is_60_40_mix_of_lx():
    """Arrêté du 18/11/2024: lx = round(0.6 · lx TGH05 + 0.4 · lx TGF05)."""
    import numpy as np

    for generation in (1900, 1950, 1960, 1985, 2005):
        h = get_table("TGH05", generation=generation).lx
        f = get_table("TGF05", generation=generation).lx
        u = get_table("TGHF05", generation=generation).lx
        expected = np.round(0.6 * h + 0.4 * f)
        assert np.array_equal(np.isnan(u), np.isnan(expected))
        assert np.array_equal(u[~np.isnan(u)], expected[~np.isnan(expected)])
