"""Tests for mortables package."""

import pytest
import numpy as np


# ===== Core =====

class TestCore:
    """Tests for table loading and MortalityTable object."""

    def test_list_tables(self):
        from mortables import list_tables
        tables = list_tables()
        ids = [t["id"] for t in tables]
        assert "TH0002" in ids
        assert "TF0002" in ids
        assert "TGH05" in ids
        assert "TGF05" in ids

    def test_load_period_table(self):
        from mortables import get_table
        th = get_table("TH0002")
        assert th.name == "TH0002"
        assert th.gender == "M"
        assert th.table_type == "period"
        assert th.lx[0] == 100000
        assert th.max_age > 90
        assert 0 < th.qx_at(0) < 0.01  # infant mortality
        assert 0 < th.qx_at(65) < 0.05

    def test_load_period_table_female(self):
        from mortables import get_table
        tf = get_table("TF0002")
        assert tf.gender == "F"
        # Women live longer on average
        th = get_table("TH0002")
        assert tf.life_expectancy(0) > th.life_expectancy(0)

    def test_aliases(self):
        from mortables import get_table
        t1 = get_table("TH0002")
        t2 = get_table("TH00-02")
        t3 = get_table("TH")
        assert t1.name == t2.name == t3.name

    def test_generational_requires_generation(self):
        from mortables import get_table
        with pytest.raises(ValueError, match="generational"):
            get_table("TGH05")

    def test_generational_table(self):
        from mortables import get_table
        tg = get_table("TGH05", generation=1960)
        assert tg.generation == 1960
        assert tg.table_type == "generational"
        assert tg.lx[0] == 100000
        assert 0 < tg.qx_at(65) < 0.05

    def test_generational_improvement(self):
        """Later generations should have lower mortality."""
        from mortables import get_table
        tg_old = get_table("TGH05", generation=1920)
        tg_new = get_table("TGH05", generation=1980)
        # At age 70, the 1980 generation should have lower qx
        assert tg_new.qx_at(70) < tg_old.qx_at(70)

    def test_generation_out_of_range(self):
        from mortables import get_table
        with pytest.raises(ValueError, match="out of range"):
            get_table("TGH05", generation=1800)

    def test_unknown_table(self):
        from mortables import get_table
        with pytest.raises(ValueError, match="Unknown"):
            get_table("NONEXISTENT")

    def test_survival_probability(self):
        from mortables import get_table
        th = get_table("TH0002")
        # Probability of surviving from 0 to 0 = 1
        assert th.survival_probability(50, 50) == 1.0
        # Should be between 0 and 1
        sp = th.survival_probability(60, 80)
        assert 0 < sp < 1

    def test_to_dataframe(self):
        from mortables import get_table
        th = get_table("TH0002")
        df = th.to_dataframe()
        assert "age" in df.columns
        assert "qx" in df.columns
        assert "lx" in df.columns
        assert "ex" in df.columns
        assert len(df) == len(th.ages)

    def test_qx_sums_sensible(self):
        """qx should be between 0 and 1 for all ages."""
        from mortables import get_table
        th = get_table("TH0002")
        assert np.all(th.qx >= 0)
        assert np.all(th.qx <= 1)

    def test_life_expectancy_range(self):
        """Life expectancy at 0 should be in a reasonable range for France."""
        from mortables import get_table
        th = get_table("TH0002")
        e0 = th.life_expectancy(0)
        assert 70 < e0 < 85  # French males, ~2000


# ===== Life =====

class TestLife:
    """Tests for actuarial functions."""

    def test_commutation_numbers(self):
        from mortables import get_table, life
        th = get_table("TH0002")
        ct = life.commutation(th, rate=0.02)
        # Dx should decrease with age
        assert ct.Dx[0] > ct.Dx[50] > ct.Dx[80]
        # Nx should decrease with age
        assert ct.Nx[0] > ct.Nx[50]
        # Mx should decrease with age
        assert ct.Mx[0] > ct.Mx[50]

    def test_annuity_due(self):
        from mortables import get_table, life
        th = get_table("TH0002")
        ad = life.annuity_due(th, age=65, rate=0.02)
        # For a 65-year-old male, annuity should be roughly 12-18
        assert 10 < ad < 25

    def test_annuity_temporary(self):
        from mortables import get_table, life
        th = get_table("TH0002")
        ad_whole = life.annuity_due(th, age=65, rate=0.02)
        ad_temp = life.annuity_due(th, age=65, rate=0.02, term=10)
        # Temporary annuity must be less than whole-life
        assert ad_temp < ad_whole
        assert ad_temp > 0

    def test_annuity_immediate_vs_due(self):
        from mortables import get_table, life
        th = get_table("TH0002")
        ad = life.annuity_due(th, age=65, rate=0.02)
        ai = life.annuity_immediate(th, age=65, rate=0.02)
        assert abs(ai - (ad - 1.0)) < 1e-10

    def test_whole_life_insurance(self):
        from mortables import get_table, life
        th = get_table("TH0002")
        ax = life.whole_life_insurance(th, age=40, rate=0.02)
        assert 0 < ax < 1  # must be between 0 and 1

    def test_term_insurance(self):
        from mortables import get_table, life
        th = get_table("TH0002")
        ti = life.term_insurance(th, age=40, rate=0.02, term=20)
        wl = life.whole_life_insurance(th, age=40, rate=0.02)
        assert 0 < ti < wl  # term < whole life

    def test_pure_endowment(self):
        from mortables import get_table, life
        th = get_table("TH0002")
        pe = life.pure_endowment(th, age=40, rate=0.02, term=20)
        assert 0 < pe < 1

    def test_endowment_insurance(self):
        from mortables import get_table, life
        th = get_table("TH0002")
        ei = life.endowment_insurance(th, age=40, rate=0.02, term=20)
        ti = life.term_insurance(th, age=40, rate=0.02, term=20)
        pe = life.pure_endowment(th, age=40, rate=0.02, term=20)
        assert abs(ei - (ti + pe)) < 1e-10

    def test_net_premium_positive(self):
        from mortables import get_table, life
        th = get_table("TH0002")
        p = life.net_premium_whole_life(th, age=30, rate=0.02)
        assert p > 0

    def test_reserve_increases(self):
        """Reserve should generally increase over time for whole-life."""
        from mortables import get_table, life
        th = get_table("TH0002")
        r5 = life.reserve_whole_life(th, age_at_issue=30, rate=0.02, duration=5)
        r20 = life.reserve_whole_life(th, age_at_issue=30, rate=0.02, duration=20)
        assert r20 > r5

    def test_identity_Ax_plus_d_ax(self):
        """Classic identity: Ax + d·äx = 1, where d = i/(1+i)."""
        from mortables import get_table, life
        th = get_table("TH0002")
        rate = 0.03
        d = rate / (1 + rate)
        for age in [20, 40, 60, 80]:
            ax = life.whole_life_insurance(th, age, rate)
            adx = life.annuity_due(th, age, rate)
            assert abs(ax + d * adx - 1.0) < 0.01, f"Identity failed at age {age}"


# ===== Cash flows =====

class TestCashflows:
    """Tests for portfolio cash-flow projections."""

    def test_project_simple(self):
        from mortables.cashflows import project
        pf = [{"age": 65, "annual_rent": 10000}]
        flows = project(pf, table="TF0002", years=30, rate=0.0)
        assert len(flows) == 31  # years 0 to 30
        # Year 0: full payment
        assert flows.iloc[0]["expected_payment"] == 10000.0
        # Payments decrease over time
        assert flows.iloc[20]["expected_payment"] < flows.iloc[0]["expected_payment"]

    def test_project_with_discount(self):
        from mortables.cashflows import project
        pf = [{"age": 65, "annual_rent": 10000}]
        flows = project(pf, table="TF0002", years=30, rate=0.03)
        # PV payments should be less than nominal
        assert flows.iloc[10]["pv_payment"] < flows.iloc[10]["expected_payment"]

    def test_total_provision(self):
        from mortables.cashflows import total_provision
        pf = [{"age": 65, "annual_rent": 10000}]
        prov = total_provision(pf, table="TF0002", years=60, rate=0.02)
        # Should be a positive number, roughly 10-20 years of rent
        assert 100000 < prov < 300000

    def test_portfolio_multiple_people(self):
        from mortables.cashflows import project
        pf = [
            {"age": 65, "annual_rent": 12000},
            {"age": 72, "annual_rent": 8000},
            {"age": 58, "annual_rent": 15000},
        ]
        flows = project(pf, table="TF0002", years=40, rate=0.02)
        # Year 0: sum of all rents
        assert flows.iloc[0]["expected_payment"] == 35000.0
