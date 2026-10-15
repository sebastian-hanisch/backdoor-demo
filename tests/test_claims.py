"""Jede Zahl aus README.md und den App-Texten wird hier über dieselben Auswertungsfunktionen nachgerechnet (DEMO-PLAYBOOK §4).

Zufallsdiagramme kommen aus SplitMix64 (ganzzahlig, plattformstabil): ihre Zählungen werden exakt geprüft. Stichprobenwerte (Deckung, Schätzungen) mit Toleranz,
damit Rundung und Bibliotheksversionen (CI installiert ungepinnt) nichts kippen.
"""

import pytest

import bdr_backdoor as B
import bdr_constants as C
import bdr_evaluation as ev


def pct(x):
    return 100 * x


@pytest.fixture(scope="module")
def sets():
    return ev.sets_experiment()


@pytest.fixture(scope="module")
def recipes():
    return ev.recipes_experiment()


@pytest.fixture(scope="module")
def criterion():
    return ev.criterion_experiment()


@pytest.fixture(scope="module")
def hidden():
    return ev.hidden_experiment()


# ----------------------------------------------------------------------------- Standard-Stichprobe und Welten

def test_default_sample_in_the_six_node_world():
    a = ev.analyse(ev.Settings())
    assert a.check.valid and len(a.check.blocked_paths) == 2 and a.truth == pytest.approx(0.5)
    assert a.estimate == pytest.approx(0.48, abs=0.01) and a.covers and a.n_valid == 8 and len(a.rows) == 16


def test_the_two_backdoor_paths_of_the_six_node_world():
    a = ev.analyse(ev.Settings(z=()))
    texts = sorted(" ".join(a.names[v] for v in p.nodes) for p in a.check.open_paths)
    assert texts == ["Faktor Schwankung Region Lieferverzug Servicegrad", "Faktor Schwankung Servicegrad"]


def test_empty_set_population_error_is_minus_0_55():
    a = ev.analyse(ev.Settings(z=()))
    assert a.pop_coef - a.truth == pytest.approx(-0.554, abs=0.002)


def test_diagrams_a_and_b_give_opposite_verdicts_for_the_same_set():
    a = ev.analyse(ev.Settings(**{k: (tuple(v) if isinstance(v, (list, tuple)) else v)
                                  for k, v in C.PRESETS["Diagramm A"].items() if k not in ("seed",)}, seed=C.DEFAULT_SEED))
    b = ev.analyse(ev.Settings(world=C.PRESETS["Diagramm B"]["world"], x=0, y=2, z=(1,)))
    assert a.check.valid and not b.check.valid
    assert B.backdoor_valid(ev.true_parents(C.PRESETS["Diagramm B"]["world"]), 0, 2, ())


def test_mediator_world_effect_is_0_7_and_everything_controlled_gives_0_3():
    p = C.PRESETS["Alles kontrollieren schadet"]
    a = ev.analyse(ev.Settings(world=p["world"], x=p["x"], y=p["y"], z=p["z"]))
    assert a.truth == pytest.approx(0.7) and a.pop_coef == pytest.approx(0.3, abs=1e-9) and not a.check.valid and a.check.descendants_in_z == (2,)
    only_z = ev.analyse(ev.Settings(world=p["world"], x=p["x"], y=p["y"], z=(0,)))
    assert only_z.pop_coef == pytest.approx(0.7, abs=1e-9) and only_z.check.valid


# ----------------------------------------------------------------------------- Experiment 1

def test_experiment_1_eight_of_sixteen_sets_are_valid_all_with_the_fluctuation(sets):
    assert sum(r["valid"] for r in sets) == 8 and all(r["valid"] == (2 in r["z"]) for r in sets)
    assert all(r["adj"] == r["valid"] for r in sets)


def test_experiment_1_coverage_valid_about_ninety_six_invalid_zero(sets):
    valid = [r["cover"] for r in sets if r["valid"]]
    invalid = [r["cover"] for r in sets if not r["valid"]]
    assert pct(sum(valid) / len(valid)) == pytest.approx(96, abs=2.5) and max(invalid) == 0.0


def test_experiment_1_population_errors_of_the_invalid_sets(sets):
    by = {r["names"]: r["bias"] for r in sets}
    assert by[()] == pytest.approx(-0.554, abs=0.002) and by[("Region",)] == pytest.approx(-0.298, abs=0.002)
    assert by[("Lieferverzug",)] == pytest.approx(-0.364, abs=0.002) and by[("Wetter",)] == pytest.approx(-0.554, abs=0.002)
    assert all(abs(r["bias"]) < 1e-9 for r in sets if r["valid"])


# ----------------------------------------------------------------------------- Experiment 2

def test_experiment_2_recipe_counts(recipes):
    assert recipes["n_all"] == 600 and recipes["n_parent"] == 242
    assert recipes["all"] == {"leere Menge": 418, "alle anderen Variablen": 84, "Eltern von x": 600, "alle Nicht-Nachfahren von x": 600, "alle Vorfahren von y": 355}
    assert recipes["with_parent"] == {"leere Menge": 60, "alle anderen Variablen": 57, "Eltern von x": 242, "alle Nicht-Nachfahren von x": 242, "alle Vorfahren von y": 169}


def test_experiment_2_valid_sets_per_diagram(recipes):
    assert sum(recipes["valid_counts"]) / 600 == pytest.approx(4.54, abs=0.01) and min(recipes["valid_counts"]) >= 1
    assert sum(recipes["min_sizes"]) / 600 == pytest.approx(0.385, abs=0.005)


# ----------------------------------------------------------------------------- Experiment 3

def test_experiment_3_the_criterion_never_fails_and_is_not_necessary(criterion):
    assert criterion["pairs"] == 6400 and criterion["diagrams"] == 400
    assert (criterion["valid_correct"], criterion["valid_wrong"], criterion["invalid_correct"], criterion["invalid_wrong"]) == (2334, 0, 903, 3163)
    assert criterion["adj_disagree"] == 0
    assert pct(criterion["invalid_correct"] / criterion["pairs"]) == pytest.approx(14.1, abs=0.1)


# ----------------------------------------------------------------------------- Experiment 4

def test_experiment_4_hidden_common_cause(hidden):
    cases, none = hidden["common"]
    assert cases + hidden["other"][0] == 800 and hidden["other"][1] == 0
    assert pct(none / cases) == pytest.approx(51, abs=1) and cases == 115
