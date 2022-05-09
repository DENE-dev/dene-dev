#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
import warnings
import pandas as pd
import pytest
from covsirphy import Scenario
from covsirphy import Term, PhaseSeries, SIR, SIRD


class TestScenario(object):
    @pytest.mark.parametrize("country", ["Italy", "Japan"])
    @pytest.mark.parametrize("province", [None, "Tokyo"])
    @pytest.mark.parametrize("tau", [None, 720, 1000])
    def test_start(self, jhu_data, population_data, country, province, tau):
        if country == "Italy" and province == "Tokyo":
            with pytest.raises(KeyError):
                Scenario(
                    jhu_data, population_data, country, province=province)
            return
        if tau == 1000:
            with pytest.raises(ValueError):
                Scenario(
                    jhu_data, population_data, country, province=province, tau=tau)
            return
        Scenario(
            jhu_data, population_data, country, province=province, tau=tau)

    @pytest.mark.parametrize("country", ["Japan"])
    def test_class_as_dict(self, jhu_data, population_data, country):
        # Setting
        snl = Scenario(jhu_data, population_data, country)
        # Create a phase series
        population = population_data.value(country)
        sr_df = jhu_data.to_sr(country=country, population=population)
        series = PhaseSeries("01Apr2020", "01Aug2020", population)
        series.trend(sr_df, show_figure=False)
        # Add scenario
        snl["New"] = series
        # Get scenario
        assert snl["New"] == series
        assert len(snl["New"]) == len(series)

    @pytest.mark.parametrize("country", ["Japan"])
    def test_start_record_range(self, jhu_data, population_data, country):
        # Setting
        snl = Scenario(jhu_data, population_data, country)
        # Test
        snl.first_date = "01Apr2020"
        assert snl.first_date == "01Apr2020"
        snl.last_date = "01May2020"
        assert snl.last_date == "01May2020"
        with pytest.raises(ValueError):
            snl.first_date = "01Jan2019"
        with pytest.raises(ValueError):
            tomorrow = Term.tomorrow(datetime.now().strftime(Term.DATE_FORMAT))
            snl.last_date = tomorrow

    @pytest.mark.parametrize("country", ["Japan"])
    def test_records(self, jhu_data, population_data, country):
        warnings.filterwarnings("ignore", category=UserWarning)
        # Setting
        snl = Scenario(jhu_data, population_data, country)
        snl.first_date = "01Apr2020"
        snl.last_date = "01Aug2020"
        # Test
        df = snl.records(show_figure=False)
        assert isinstance(df, pd.DataFrame)
        assert set(df.columns) == set(Term.NLOC_COLUMNS)
        dates = df[Term.DATE]
        assert dates.min() == Term.date_obj(snl.first_date)
        assert dates.max() == Term.date_obj(snl.last_date)
        df2 = snl.records(show_figure=True)
        assert isinstance(df2, pd.DataFrame)
        assert set(df2.columns) == set(Term.NLOC_COLUMNS)

    @pytest.mark.parametrize("country", ["Japan"])
    def test_edit_series(self, jhu_data, population_data, country):
        # Setting
        snl = Scenario(jhu_data, population_data, country)
        snl.first_date = "01Apr2020"
        snl.last_date = "01Aug2020"
        # Add and clear
        assert snl.summary().empty
        snl.add(end_date="05May2020")
        snl.add(days=20)
        snl.add()
        snl.add(end_date="01Sep2020")
        assert len(snl["Main"]) == 4
        snl.clear(include_past=True)
        snl.add(end_date="01Sep2020", name="New")
        assert len(snl["New"]) == 2
        # Delete
        snl.delete(name="Main")
        assert len(snl["Main"]) == 0
        with pytest.raises(TypeError):
            snl.delete(phases="1st", name="New")
        snl.delete(phases=["1st"], name="New")
        assert len(snl["New"]) == 1
        snl.delete(name="New")
        with pytest.raises(KeyError):
            assert len(snl["New"]) == 1

    @pytest.mark.parametrize("country", ["Japan"])
    def test_add_phase_dep(self, jhu_data, population_data, country):
        # Setting
        snl = Scenario(jhu_data, population_data, country)
        snl.first_date = "01Apr2020"
        snl.last_date = "01Aug2020"
        # Test
        warnings.simplefilter("error")
        with pytest.raises(DeprecationWarning):
            snl.add_phase(end_date="01May2020")

    @pytest.mark.parametrize("country", ["Japan"])
    def test_trend(self, jhu_data, population_data, country):
        # Setting
        snl = Scenario(jhu_data, population_data, country)
        snl.first_date = "01Apr2020"
        snl.last_date = "01Aug2020"
        snl.trend(show_figure=False)
        assert snl["Main"]
        with pytest.raises(ValueError):
            snl.trend(show_figure=False, n_points=3)
        # Disable/enable
        length = len(snl["Main"])
        snl.enable(phases=["0th"], name="Main")
        assert len(snl["Main"]) == length + 1
        snl.disable(phases=["0th"], name="Main")
        assert len(snl["Main"]) == length
        with pytest.raises(TypeError):
            snl.enable(phases="0th", name="Main")
        with pytest.raises(TypeError):
            snl.disable(phases="1st", name="Main")

    @pytest.mark.parametrize("country", ["Japan"])
    def test_edit(self, jhu_data, population_data, country):
        # Setting
        snl = Scenario(jhu_data, population_data, country)
        snl.first_date = "01Apr2020"
        snl.last_date = "01Aug2020"
        snl.trend(show_figure=False)
        # Combine
        length = len(snl["Main"])
        snl.combine(["1st", "2nd", "3rd"])
        assert len(snl["Main"]) == length - 2
        # Separate
        with pytest.raises(IndexError):
            snl.separate(date="01Dec2020")
        snl.separate(date="01May2020")
        assert len(snl["Main"]) == length - 1

    @pytest.mark.parametrize("country", ["Japan"])
    def test_summary(self, jhu_data, population_data, country):
        # Setting
        snl = Scenario(jhu_data, population_data, country)
        snl.first_date = "01Apr2020"
        snl.last_date = "01Aug2020"
        snl.trend(show_figure=False)
        # One scenario
        assert set(snl.summary().columns) == set(
            [Term.TENSE, Term.START, Term.END, Term.N])
        # Show two scenarios
        snl.clear(name="New")
        cols = snl.summary().reset_index().columns
        assert set([Term.SERIES, Term.PHASE]).issubset(set(cols))
        # Show selected scenario
        cols_sel = snl.summary(name="New").reset_index().columns
        assert not set([Term.SERIES, Term.PHASE]).issubset(set(cols_sel))
        # Columns to show
        show_cols = [Term.N, Term.START]
        assert set(snl.summary(columns=show_cols).columns) == set(show_cols)
        with pytest.raises(TypeError):
            snl.summary(columns=Term.N)
        with pytest.raises(KeyError):
            snl.summary(columns=[Term.N, "Temperature"])

    @pytest.mark.parametrize("country", ["Japan"])
    def test_estimate(self, jhu_data, population_data, country):
        warnings.filterwarnings("ignore", category=UserWarning)
        # Setting
        snl = Scenario(jhu_data, population_data, country)
        snl.first_date = "01Apr2020"
        snl.last_date = "01Aug2020"
        with pytest.raises(ValueError):
            snl.estimate(SIR)
        snl.trend(show_figure=False)
        with pytest.raises(KeyError):
            snl.estimate_history(phase="1th")
            # Parameter estimation
        with pytest.raises(TypeError):
            snl.estimate(model=SIR, phase="1st")
        with pytest.raises(KeyError):
            snl.estimate(SIR, phases=["0th"])
        snl.estimate(SIR, phase=["1st", "2nd"])
        snl.estimate(SIR)
        # Estimation history
        snl.estimate_history()
        # Estimation accuracy
        snl.estimate_accuracy()
        # Get a value
        snl.get(Term.RT)

    @pytest.mark.parametrize("country", ["Japan"])
    def test_simulate(self, jhu_data, population_data, country):
        warnings.filterwarnings("ignore", category=UserWarning)
        # Setting
        snl = Scenario(jhu_data, population_data, country)
        snl.first_date = "01Apr2020"
        snl.last_date = "01Aug2020"
        snl.trend(show_figure=False)
        # Parameter estimation
        snl.estimate(SIR, phase=["1st", "2nd"])
        with pytest.raises(KeyError):
            snl.simulate()
        snl.estimate(SIR)
        # Simulation
        snl.simulate()
        # Add a phase with different model
        snl.add(days=30, model=SIRD)
        with pytest.raises(ValueError):
            snl.simulate()
        snl.delete(phases=["last"])
        snl.add(days=30, model=SIRD, kappa=0.03)
        with pytest.raises(KeyError):
            snl.simulate()
        snl.simulate(y0_dict={Term.R: 0, Term.F: 0})
        # Parameter histpry
        snl.param_history([Term.RT])
        # Comparison of scenarios
        snl.describe(y0_dict={Term.R: 0, Term.F: 0})