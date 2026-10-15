"""Auswertung: Welten, Population, Regression, Analyse der Einstellungen, Zufallsdiagramme, Struktur der Experimente (klein gerechnet), Verdikte."""

import numpy as np
import pytest

import bdr_constants as C
import bdr_evaluation as ev
import dsep_graph as G
from kausal_generator import SplitMix64


def test_de_and_signed():
    assert ev.de(1.5, 1) == "1,5" and ev.de(-0.05, 2) == "−0,05"
    assert ev.signed(0.5, 2) == "+0,50" and ev.signed(-0.5, 2) == "−0,50" and ev.signed(-0.004, 2) == "−0,00"


@pytest.mark.parametrize("world", C.WORLD_ORDER)
def test_every_world_is_valid(world):
    w = C.WORLDS[world]
    n = len(w["nodes"])
    assert len(w["pos"]) == n and all(0 <= i < j < n for (i, j) in w["coefs"])
    x, y, z, hidden = w["query"]
    assert x != y and x not in z and y not in z and set(z).isdisjoint(hidden) and all(0 <= v < n for v in (x, y, *z, *hidden))
    scm = ev.world_scm(world)
    assert scm.names == w["nodes"] and G.edges_of(scm.parents) == tuple(sorted(w["coefs"]))
    assert ev.true_parents(world) == scm.parents


def test_population_of_the_confounded_instance_by_hand(confounded):
    _, b = confounded
    cov, total = ev.population(b)
    assert cov[1, 1] == pytest.approx(2.0) and cov[1, 2] == pytest.approx(3.0) and total[2, 1] == pytest.approx(2.0)
    assert ev.population_coefficient(cov, 1, 2, ()) == pytest.approx(1.5) and ev.population_coefficient(cov, 1, 2, (0,)) == pytest.approx(2.0)


def test_population_of_the_mediator_instance_by_hand(mediator):
    _, b = mediator
    cov, total = ev.population(b)
    assert total[3, 1] == pytest.approx(0.7)
    got = {z: ev.population_coefficient(cov, 1, 3, z) for z in ((), (0,), (2,), (0, 2))}
    assert got[(0,)] == pytest.approx(0.7) and got[()] == pytest.approx(0.2) and got[(2,)] == pytest.approx(-0.2) and got[(0, 2)] == pytest.approx(0.3)


def test_ols_coefficient_recovers_the_effect_with_a_valid_set():
    scm = ev.world_scm("6-Knoten-Beispiel")
    from kausal_generator import sample

    d = sample(scm, 20000, SplitMix64(3))
    est, se = ev.ols_coefficient(d["Servicegrad"], d["Faktor"], [d["Schwankung"]])
    assert abs(est[0] - 0.5) < 4 * se[0]
    est0, se0 = ev.ols_coefficient(d["Servicegrad"], d["Faktor"], [])
    assert abs(est0[0] - 0.5) > 10 * se0[0]


def test_covers_is_inclusive_at_the_boundary():
    assert ev.covers(np.array([0.0]), np.array([1.0]), C.Z_CRIT).tolist() == [True]
    assert ev.covers(np.array([0.0]), np.array([1.0]), C.Z_CRIT + 1e-6).tolist() == [False]


def test_random_dag_is_acyclic_in_index_order_and_reproducible():
    a = ev.random_dag(6, 0.5, SplitMix64(1))
    assert a == ev.random_dag(6, 0.5, SplitMix64(1)) and a != ev.random_dag(6, 0.5, SplitMix64(2))
    assert all(p < j for j, ps in enumerate(a) for p in ps)
    assert ev.random_dag(6, 0.0, SplitMix64(1)) == ((),) * 6
    assert sum(len(p) for p in ev.random_dag(6, 1.0, SplitMix64(1))) == 15


def test_random_coefficients_have_the_declared_range_and_sign_mix():
    parents = ev.random_dag(6, 1.0, SplitMix64(4))
    b = ev.random_coefficients(parents, SplitMix64(5))
    vals = b[b != 0]
    assert len(vals) == 15 and (np.abs(vals) >= C.COEF_LO).all() and (np.abs(vals) <= C.COEF_HI).all() and (vals > 0).any() and (vals < 0).any()


# ----------------------------------------------------------------------------- Analyse

def test_analysis_of_the_default_settings():
    a = ev.analyse(ev.Settings())
    assert a.check.valid and a.adjustment and len(a.check.blocked_paths) == 2 and a.check.open_paths == ()
    assert a.truth == pytest.approx(0.5) and a.pop_coef == pytest.approx(0.5, abs=1e-9)
    assert a.n_valid == 8 and len(a.rows) == 16 and not a.no_valid_set
    assert a.lo < a.estimate < a.hi and a.covers == (a.lo <= a.truth <= a.hi)
    assert ev.verdict_instance(a)[0] == "success" and ev.verdict_no_valid_set(a) is None


def test_the_empty_set_is_invalid_and_its_population_error_is_the_hand_value():
    a = ev.analyse(ev.Settings(z=()))
    assert not a.check.valid and len(a.check.open_paths) == 2 and not a.adjustment
    assert a.pop_coef - a.truth == pytest.approx(-0.554, abs=0.002)
    kind, text = ev.verdict_instance(a)
    assert kind == "warning" and "ungültig" in text and "2 Rückwege" in text


def test_world_b_the_same_set_gets_the_opposite_verdict():
    p = C.PRESETS["Diagramm B"]
    a = ev.analyse(ev.Settings(world=p["world"], x=p["x"], y=p["y"], z=p["z"]))
    assert not a.check.valid and a.check.descendants_in_z == (1,) and a.adjustment is False
    b = ev.analyse(ev.Settings(world=p["world"], x=p["x"], y=p["y"], z=()))
    assert b.check.valid and b.truth == pytest.approx(0.5 + 0.8 * 0.4)
    assert "Nachfahre" in ev.verdict_instance(a)[1]


def test_everything_controlled_in_the_mediator_world_gives_only_the_direct_effect():
    p = C.PRESETS["Alles kontrollieren schadet"]
    a = ev.analyse(ev.Settings(world=p["world"], x=p["x"], y=p["y"], z=p["z"], n=5000))
    assert not a.check.valid and a.truth == pytest.approx(0.7) and a.pop_coef == pytest.approx(0.3, abs=1e-9)
    assert a.estimate == pytest.approx(0.3, abs=0.1) and not a.covers


def test_hidden_confounder_leaves_no_valid_set():
    p = C.PRESETS["Eine Variable fehlt"]
    a = ev.analyse(ev.Settings(world=p["world"], x=p["x"], y=p["y"], z=p["z"], hidden=p["hidden"]))
    assert a.no_valid_set and a.n_valid == 0 and a.candidates == (0, 1, 4)
    kind, text = ev.verdict_no_valid_set(a)
    assert kind == "warning" and "keine gültige Menge" in text


def test_info_verdict_when_backdoor_is_invalid_but_the_wider_criterion_allows_it(monkeypatch):
    """Testwelt x -> c <- w, x -> y, w -> y: {w, c} ist nach Backdoor ungültig (c Nachfahre von x), nach dem Adjustierungskriterium gültig."""
    monkeypatch.setitem(C.WORLDS, "Testwelt", {"nodes": ("x", "w", "c", "y"), "coefs": {(0, 2): 0.7, (1, 2): 0.7, (0, 3): 0.5, (1, 3): 0.5},
                                               "pos": ((0, 0), (1, 1), (0.5, 0), (1, 0)), "query": (0, 3, (1, 2), ()), "help": ""})
    a = ev.analyse(ev.Settings(world="Testwelt", x=0, y=3, z=(1, 2), n=3000))
    assert not a.check.valid and a.adjustment and a.check.descendants_in_z == (2,)
    assert a.pop_coef == pytest.approx(a.truth, abs=1e-9)
    kind, text = ev.verdict_instance(a)
    assert kind == "info" and "allgemeinere Adjustierungskriterium" in text
    b = ev.analyse(ev.Settings(world="Testwelt", x=0, y=3, z=(2,)))
    assert not b.adjustment and ev.verdict_instance(b)[0] == "warning"


def test_set_rows_carry_the_population_error_and_the_candidates_include_the_last_node():
    a = ev.analyse(ev.Settings(z=(), x=0, y=1))          # Region -> Wetter: kein Pfad, Kandidaten schließen den letzten Knoten ein
    assert a.candidates == (2, 3, 4, 5) and len(a.rows) == 16
    b = ev.analyse(ev.Settings(z=()))
    by = {r.z: r for r in b.rows}
    assert by[()].bias == pytest.approx(-0.554, abs=0.002) and by[(2,)].bias == pytest.approx(0.0, abs=1e-9) and by[(0,)].bias == pytest.approx(-0.298, abs=0.002)
    assert ev.observed_candidates(6, 3, 5, (2,)) == (0, 1, 4) and ev.observed_candidates(6, 0, 1, ()) == (2, 3, 4, 5)


def test_instance_verdict_lists_the_set_in_ascending_order():
    a = ev.analyse(ev.Settings(z=(4, 2)))
    assert "Schwankung, Lieferverzug" in ev.verdict_instance(a)[1]


# ----------------------------------------------------------------------------- Experimente

def test_sets_experiment_structure():
    rows = ev.sets_experiment(n=400, reps=60)
    assert len(rows) == 16 and sum(r["valid"] for r in rows) == 8 and all(r["valid"] == (2 in r["z"]) for r in rows)
    for r in rows:
        if r["valid"]:
            assert abs(r["bias"]) < 1e-9 and r["cover"] > 0.85
        else:
            assert r["bias"] < -0.25 and r["cover"] < 0.2


def test_recipes_experiment_counts_are_consistent():
    res = ev.recipes_experiment(diagrams=80)
    assert res["n_all"] == 80 and 0 < res["n_parent"] <= 80
    assert res["all"]["Eltern von x"] == 80 and res["all"]["alle Nicht-Nachfahren von x"] == 80
    assert res["with_parent"]["Eltern von x"] == res["n_parent"]
    assert res["all"]["alle anderen Variablen"] < 80 and len(res["valid_counts"]) == 80 and min(res["valid_counts"]) >= 1


def test_criterion_experiment_has_no_counterexample():
    c = ev.criterion_experiment(diagrams=40)
    assert c["valid_wrong"] == 0 and c["adj_disagree"] == 0 and c["diagrams"] == 40
    assert c["pairs"] == 40 * 16 and c["valid_correct"] > 0 and c["invalid_correct"] > 0 and c["invalid_wrong"] > 0


def test_hidden_experiment_structure():
    h = ev.hidden_experiment(diagrams=120)
    assert h["common"][0] + h["other"][0] == 120 and h["common"][1] <= h["common"][0]
    assert h["other"][1] == 0


# ----------------------------------------------------------------------------- Verdikte

def test_verdict_texts_quote_the_numbers_they_are_given():
    rows = [{"valid": True, "cover": 0.96}, {"valid": True, "cover": 0.97}, {"valid": False, "cover": 0.0}]
    kind, text = ev.verdict_sets(rows)
    assert kind == "info" and "2 von 3" in text and "96,5 %" in text and "0,0 %" in text
    res = {"n_all": 100, "n_parent": 40, "all": {"alle anderen Variablen": 18}, "with_parent": {"alle anderen Variablen": 12}}
    kind, text = ev.verdict_recipes(res)
    assert kind == "warning" and "18 %" in text and "30 %" in text
    c = {"valid_correct": 100, "valid_wrong": 0, "invalid_correct": 14, "invalid_wrong": 50, "adj_disagree": 0, "pairs": 164}
    kind, text = ev.verdict_criterion(c)
    assert kind == "success" and "100 gültigen Mengen treffen 100" in text and "14 ungültige" in text and "0 von 164" in text
    c2 = dict(c, valid_correct=98, valid_wrong=2)
    assert "100 gültigen Mengen treffen 98 die Wirkung (2 Ausnahmen)" in ev.verdict_criterion(c2)[1]
    kind, text = ev.verdict_hidden({"common": [100, 41], "other": [700, 0]})
    assert kind == "warning" and "41 %" in text and "100 Fällen" in text and "700" in text
