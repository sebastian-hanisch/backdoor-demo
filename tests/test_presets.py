"""Presets: Vollständigkeit, gültige Werte, Urteile der Presets; Reglergrenzen und Hilfen."""

import bdr_constants as C
import bdr_evaluation as ev
import bdr_presets as P


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP)
    for name, p in C.PRESETS.items():
        assert set(p) == {"world", "x", "y", "z", "hidden", "n", "seed"}, name
        assert C.PRESET_HELP[name]


def test_preset_values_are_valid():
    for name, p in C.PRESETS.items():
        n = len(C.WORLDS[p["world"]]["nodes"])
        nodes = {p["x"], p["y"], *p["z"], *p["hidden"]}
        assert p["x"] != p["y"] and all(0 <= v < n for v in nodes), name
        assert p["x"] not in p["z"] and p["y"] not in p["z"] and set(p["z"]).isdisjoint(p["hidden"]), name
        assert C.N_MIN <= p["n"] <= C.N_MAX and (p["n"] - C.N_MIN) % C.N_STEP == 0 and 0 <= p["seed"] <= C.SEED_MAX, name


def test_default_world_and_every_world_has_a_preset():
    assert C.PRESETS["6-Knoten-Beispiel (Voreinstellung)"]["world"] == C.DEFAULT_WORLD
    assert {p["world"] for p in C.PRESETS.values()} == set(C.WORLDS)
    assert ev.Settings() == ev.Settings(**{k: (tuple(v) if isinstance(v, (list, tuple)) else v)
                                           for k, v in C.PRESETS["6-Knoten-Beispiel (Voreinstellung)"].items()})


def test_the_presets_show_different_verdicts():
    out = {}
    for name, p in C.PRESETS.items():
        a = ev.analyse(ev.Settings(world=p["world"], x=p["x"], y=p["y"], z=tuple(p["z"]), hidden=tuple(p["hidden"]), n=p["n"], seed=p["seed"]))
        out[name] = (a.check.valid, a.no_valid_set)
    assert out["6-Knoten-Beispiel (Voreinstellung)"] == (True, False)
    assert out["Diagramm A"] == (True, False)
    assert out["Diagramm B"] == (False, False)
    assert out["Alles kontrollieren schadet"] == (False, False)
    assert out["Eine Variable fehlt"] == (False, True)


def test_bounds_and_step_grid():
    assert P.bounds("n_slider") == (C.N_MIN, C.N_MAX) and P.bounds("seed_input") == (0, C.SEED_MAX)
    assert C.DEFAULT_N in range(C.N_MIN, C.N_MAX + 1, C.N_STEP)
    assert P.n_nodes("Mediator-Welt") == 4 and P.n_nodes("6-Knoten-Beispiel") == 6


def test_experiment_constants_are_consistent():
    assert C.RANDOM_P_LO < C.RANDOM_P_HI and C.COEF_LO < C.COEF_HI and C.EXP_SETS_REPS >= 200
    assert C.RANDOM_NODES == 6 and C.RANDOM_NODES_HIDDEN == 7
