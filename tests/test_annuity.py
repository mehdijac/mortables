"""
Tests for v0.2 annuity features: fractional ages, payment frequency,
deferral, guaranteed period, reversion, age shifts and qx scaling.

External reference: SPAC Actuaires, « Retraite supplémentaire – Table non
genrée » (11/2024).  Annual annuity in arrears, liquidated in 2025, technical
rate 1.75 %, 60 % reversion to a spouse of the opposite sex and same age:
annual rent for a capital of 1 000 €.
"""

import datetime as dt

import numpy as np
import pytest

from mortables import get_table, life

# age: (TGH05, TGF05, TGH05 rév., TGF05 rév., TGHF05, TGHF05 rév.)
SPAC_2025 = {
    45: (32.08, 30.62, 29.99, 29.47, 31.48, 29.88),
    50: (35.00, 33.06, 32.35, 31.66, 34.20, 32.20),
    55: (38.82, 36.16, 35.37, 34.44, 37.71, 35.16),
    60: (43.88, 40.23, 39.33, 38.09, 42.34, 39.05),
    65: (51.04, 45.85, 44.77, 43.06, 48.81, 44.38),
    70: (61.48, 53.92, 52.52, 50.12, 58.17, 51.96),
    75: (77.09, 66.07, 63.92, 60.57, 72.13, 63.11),
}


def _rent(table, age, **kw):
    value = life.annuity(table, age, 0.0175, timing="arrears", **kw)
    return round(1000 / value, 2)


@pytest.mark.parametrize("age", sorted(SPAC_2025))
def test_spac_reference_rents(age):
    h, f, hr, fr, u, ur = SPAC_2025[age]
    gen = 2025 - age
    tgh = get_table("TGH05", generation=gen)
    tgf = get_table("TGF05", generation=gen)
    tghf = get_table("TGHF05", generation=gen)
    assert _rent(tgh, age) == h
    assert _rent(tgf, age) == f
    assert _rent(tgh, age, reversion=0.6, spouse_table=tgf, spouse_age=age) == hr
    assert _rent(tgf, age, reversion=0.6, spouse_table=tgh, spouse_age=age) == fr
    assert _rent(tghf, age) == u
    assert _rent(tghf, age, reversion=0.6, spouse_table=tghf, spouse_age=age) == ur


# ----- Consistency with the annual functions --------------------------------

@pytest.fixture
def th():
    return get_table("TH0002")


@pytest.mark.parametrize("rate", [-0.005, 0.0, 0.02])
def test_annual_matches_annuity_due(th, rate):
    for age in (30, 65, 100):
        assert life.annuity(th, age, rate) == pytest.approx(
            life.annuity_due(th, age, rate), rel=1e-12
        )
        assert life.annuity(th, age, rate, timing="arrears") == pytest.approx(
            life.annuity_immediate(th, age, rate), rel=1e-12, abs=1e-12
        )


def test_term_matches_temporary_annuity(th):
    assert life.annuity(th, 65, 0.02, term=10) == pytest.approx(
        life.annuity_due(th, 65, 0.02, term=10), rel=1e-12
    )


def test_deferred_matches_pure_endowment(th):
    expected = life.pure_endowment(th, 55, 0.02, 10) * life.annuity_due(th, 65, 0.02)
    assert life.annuity(th, 55, 0.02, deferred=10) == pytest.approx(expected, rel=1e-12)


@pytest.mark.parametrize("m", [2, 4, 12])
@pytest.mark.parametrize("rate", [0.01, 0.03])
def test_fractional_payments_udd_closed_form(th, m, rate):
    """Under UDD: ä(m) = α(m)·ä − β(m), exactly."""
    i = rate
    d = i / (1 + i)
    im = m * ((1 + i) ** (1 / m) - 1)
    dm = m * (1 - (1 + i) ** (-1 / m))
    alpha = i * d / (im * dm)
    beta = (i - im) / (im * dm)
    for age in (40, 65, 90):
        expected = alpha * life.annuity_due(th, age, i) - beta
        got = life.annuity(th, age, i, frequency=m)
        assert got == pytest.approx(expected, rel=1e-10)
        # arrears = advance − 1/m
        arrears = life.annuity(th, age, i, frequency=m, timing="arrears")
        assert arrears == pytest.approx(got - 1 / m, rel=1e-10)


def test_monthly_close_to_woolhouse(th):
    ad = life.annuity_due(th, 65, 0.02)
    assert life.annuity(th, 65, 0.02, frequency=12) == pytest.approx(
        ad - 11 / 24, abs=0.01
    )


def test_guaranteed_beyond_lifetime_is_annuity_certain(th):
    got = life.annuity(th, 65, 0.02, guaranteed=56)
    assert got == pytest.approx(sum(1.02 ** -k for k in range(56)), rel=1e-12)


def test_guaranteed_increases_value(th):
    base = life.annuity(th, 65, 0.02, frequency=12)
    assert life.annuity(th, 65, 0.02, frequency=12, guaranteed=10) > base


def test_reversion_bounds(th):
    tf = get_table("TF0002")
    single = life.annuity(th, 65, 0.02)
    full = life.annuity(th, 65, 0.02, reversion=1.0, spouse_table=tf, spouse_age=62)
    sixty = life.annuity(th, 65, 0.02, reversion=0.6, spouse_table=tf, spouse_age=62)
    assert single < sixty < full
    # last-survivor identity: ä(xy-bar) = äx + äy − äxy
    ax = life.annuity_due(th, 65, 0.02)
    ay = life.annuity_due(tf, 62, 0.02)
    axy = sum(
        1.02 ** -k * th.tpx(65, k) * tf.tpx(62, k) for k in range(60)
    )
    assert full == pytest.approx(ax + ay - axy, rel=1e-12)


# ----- Fractional ages & dates -----------------------------------------------

def test_lx_linear_interpolation(th):
    assert th.lx_at(65.5) == (th.lx[65] + th.lx[66]) / 2
    assert th.lx_at(65) == th.lx[65]
    assert th.lx_at(th.max_age + 1) == 0.0
    assert th.tpx(65, 0) == 1.0


def test_fractional_age_between_integer_ages(th):
    a65 = life.annuity(th, 65, 0.02)
    a66 = life.annuity(th, 66, 0.02)
    assert a66 < life.annuity(th, 65.5, 0.02) < a65


def test_exact_age_conventions():
    assert life.exact_age("1961-03-15", "2026-12-31") == pytest.approx(
        (dt.date(2026, 12, 31) - dt.date(1961, 3, 15)).days / 365.25
    )
    assert life.exact_age("1961-03-15", "2026-12-31", "months") == 65 + 9 / 12
    assert life.exact_age("1961-03-15", "2026-03-14", "years") == 64
    assert life.exact_age(dt.date(1961, 3, 15), dt.date(2026, 3, 15), "years") == 65
    with pytest.raises(ValueError):
        life.exact_age("2000-01-01", "1999-01-01")


def test_dates_pick_generation_and_age():
    by_dates = life.annuity(
        "TGH05", birth_date="1961-03-15", valuation_date="2026-12-31", rate=0.02,
        frequency=12, reversion=0.6, spouse_table="TGF05",
        spouse_birth_date="1963-07-02",
    )
    x = life.exact_age("1961-03-15", "2026-12-31")
    y = life.exact_age("1963-07-02", "2026-12-31")
    explicit = life.annuity(
        get_table("TGH05", generation=1961), x, 0.02, frequency=12,
        reversion=0.6, spouse_table=get_table("TGF05", generation=1963), spouse_age=y,
    )
    assert by_dates == pytest.approx(explicit, rel=1e-14)


# ----- Validation --------------------------------------------------------------

@pytest.mark.parametrize(
    "kwargs",
    [
        {"frequency": 0},
        {"frequency": 1.5},
        {"timing": "monthly"},
        {"reversion": 1.5},
        {"reversion": 0.6},  # no spouse
        {"deferred": -1},
        {"term": 5, "guaranteed": 10},
    ],
)
def test_invalid_annuity_inputs(th, kwargs):
    with pytest.raises(ValueError):
        life.annuity(th, 65, 0.02, **kwargs)


def test_age_before_generation_start_raises():
    with pytest.raises(ValueError, match="out of range"):
        life.annuity(get_table("TGH05", generation=1950), 40.5, 0.02)


# ----- Adjusted tables -----------------------------------------------------------

def test_age_shift(th):
    older = th.age_shifted(2)
    assert older.qx[60] == pytest.approx(th.qx[62])
    assert life.annuity(older, 65, 0.02) < life.annuity(th, 65, 0.02)
    younger = get_table("TGH05", generation=1950).age_shifted(-3)
    assert younger.min_age == 49
    assert np.nanmax(np.abs(th.age_shifted(0).lx - th.lx)) < 1e-6


def test_scaled_solvency_shocks(th):
    longevity = th.scaled(0.8)
    mortality = th.scaled(1.15)
    assert longevity.qx[60] == pytest.approx(0.8 * th.qx[60])
    assert longevity.qx[-1] == 1.0
    assert np.all(mortality.qx <= 1.0)
    base = life.annuity(th, 65, 0.02)
    assert life.annuity(longevity, 65, 0.02) > base > life.annuity(mortality, 65, 0.02)
    assert longevity.metadata["adjustments"] == [{"type": "scale", "factor": 0.8}]
    with pytest.raises(ValueError):
        th.scaled(-1)
