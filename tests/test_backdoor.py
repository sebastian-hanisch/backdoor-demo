"""Kern: kausale Pfade, Rückwege, Backdoor- und Adjustierungskriterium, gültige Mengen, Rezepte; an den Mini-Instanzen von Hand."""

import pytest

import bdr_backdoor as B
import bdr_evaluation as ev
import dsep_graph as G


# ----------------------------------------------------------------------------- Pfade

def test_directed_paths_of_the_mediator_instance(mediator):
    parents, _ = mediator
    assert B.directed_paths(parents, 1, 3) == [(1, 2, 3), (1, 3)]
    assert B.directed_paths(parents, 0, 3) == [(0, 1, 2, 3), (0, 1, 3), (0, 3)]
    assert B.directed_paths(parents, 3, 1) == []


def test_backdoor_paths_of_the_confounded_instance(confounded):
    parents, _ = confounded
    (p,) = B.backdoor_paths(parents, 1, 2)
    assert p.nodes == (1, 0, 2) and p.arrows == ("←", "→") and not p.blocked
    (q,) = B.backdoor_paths(parents, 1, 2, (0,))
    assert q.blocked and q.kind == "bedingt" and q.blocker == 0


def test_the_direct_edge_is_not_a_backdoor_path(confounded):
    parents, _ = confounded
    assert all(p.nodes != (1, 2) for p in B.backdoor_paths(parents, 1, 2))


# ----------------------------------------------------------------------------- Backdoor-Kriterium an den Mini-Instanzen

def test_confounded_instance_empty_set_invalid_and_confounder_valid(confounded):
    parents, _ = confounded
    r = B.backdoor_check(parents, 1, 2, ())
    assert not r.valid and len(r.open_paths) == 1 and r.descendants_in_z == ()
    r = B.backdoor_check(parents, 1, 2, (0,))
    assert r.valid and len(r.blocked_paths) == 1 and r.open_paths == ()


def test_mediator_instance_by_hand(mediator):
    parents, _ = mediator
    assert B.backdoor_valid(parents, 1, 3, (0,))
    assert not B.backdoor_valid(parents, 1, 3, ())
    assert not B.backdoor_valid(parents, 1, 3, (2,))                 # Nachfahre, und der Rückweg bleibt offen
    r = B.backdoor_check(parents, 1, 3, (0, 2))
    assert not r.valid and r.descendants_in_z == (2,) and r.open_paths == ()


def test_the_adjustment_criterion_is_wider_by_a_descendant_off_the_causal_path():
    """0 = x, 1 = w, 2 = c, 3 = y mit x -> c <- w, x -> y, w -> y. Kein Pfeil führt in x hinein, also ist die leere Menge gültig. {c} öffnet den Collider c und
    ist nach beiden Kriterien ungültig; {w, c} blockiert den geöffneten Pfad x -> c <- w -> y bei w: nach Backdoor ungültig (c ist Nachfahre von x), nach dem
    Adjustierungskriterium gültig."""
    parents = ((), (), (0, 1), (0, 1))
    assert B.backdoor_valid(parents, 0, 3, ()) and B.adjustment_valid(parents, 0, 3, ())
    assert not B.backdoor_valid(parents, 0, 3, (2,)) and not B.adjustment_valid(parents, 0, 3, (2,))
    assert not B.backdoor_valid(parents, 0, 3, (1, 2)) and B.adjustment_valid(parents, 0, 3, (1, 2))
    assert B.backdoor_valid(parents, 0, 3, (1,)) and B.adjustment_valid(parents, 0, 3, (1,))


def test_mediator_is_forbidden_for_both_criteria(mediator):
    parents, _ = mediator
    assert B.forbidden_nodes(parents, 1, 3) == {2, 3}
    assert not B.adjustment_valid(parents, 1, 3, (2,)) and not B.adjustment_valid(parents, 1, 3, (0, 2))
    assert B.adjustment_valid(parents, 1, 3, (0,)) and not B.adjustment_valid(parents, 1, 3, ())


def test_without_a_causal_path_descendants_are_not_forbidden():
    parents = ((), (0,), (0,))                       # x = 1 und y = 2 sind Geschwister (Gabel über 0)
    assert B.directed_paths(parents, 1, 2) == [] and B.forbidden_nodes(parents, 1, 2) == set()
    assert B.adjustment_valid(parents, 1, 2, (0,)) and not B.adjustment_valid(parents, 1, 2, ())


def test_checks_refuse_x_or_y_in_the_set_and_x_equal_y(confounded):
    parents, _ = confounded
    for f in (B.backdoor_check, B.adjustment_valid):
        with pytest.raises(ValueError):
            f(parents, 1, 2, (1,))
        with pytest.raises(ValueError):
            f(parents, 1, 1, ())


# ----------------------------------------------------------------------------- Mengen und Rezepte

def test_valid_sets_of_the_confounded_instance(confounded):
    parents, _ = confounded
    assert B.valid_sets(parents, 1, 2, [0]) == [(0,)]
    assert B.valid_sets(parents, 1, 2, []) == []                   # ohne beobachtetes Z gibt es keine gültige Menge
    assert B.valid_sets(parents, 1, 2, [0], criterion="adjustment") == [(0,)]


def test_valid_sets_of_the_mediator_instance(mediator):
    parents, _ = mediator
    assert B.valid_sets(parents, 1, 3, [0, 2]) == [(0,)]


def test_all_sets_and_minimal_sets():
    assert B.all_sets([2, 0]) == [(), (0,), (2,), (0, 2)]
    assert sorted(B.minimal_sets([(0,), (0, 1), (1, 2), (0, 1, 2)])) == [(0,), (1, 2)]
    assert B.minimal_sets([()]) == [()]


def test_standard_recipes_by_hand(mediator):
    parents, _ = mediator
    r = B.standard_recipes(parents, 1, 3)
    assert r["leere Menge"] == () and r["alle anderen Variablen"] == (0, 2) and r["Eltern von x"] == (0,)
    assert r["alle Nicht-Nachfahren von x"] == (0,) and r["alle Vorfahren von y"] == (0, 2)
    assert B.backdoor_valid(parents, 1, 3, r["Eltern von x"]) and not B.backdoor_valid(parents, 1, 3, r["alle anderen Variablen"])


def test_parents_of_x_and_all_non_descendants_are_always_valid_on_random_diagrams():
    from kausal_generator import SplitMix64

    rng = SplitMix64(5)
    checked = 0
    while checked < 150:
        parents = ev.random_dag(6, 0.45, rng)
        x, y = 2, 5
        r = B.standard_recipes(parents, x, y)
        assert B.backdoor_valid(parents, x, y, r["Eltern von x"])
        assert B.backdoor_valid(parents, x, y, r["alle Nicht-Nachfahren von x"])
        checked += 1


def test_tuples_in_results_are_sorted_ascending():
    parents = ((), (), (0, 1), (2,), (1, 2))        # x = 2 mit den Eltern 0 und 1, 2 -> 3, y = 4 mit den Eltern 1 und 2
    assert B.standard_recipes(parents, 2, 4)["Eltern von x"] == (0, 1)
    r = B.backdoor_check(parents, 2, 4, (3, 0))
    assert r.descendants_in_z == (3,)
    wide = ((), (0,), (0,), (1, 2), (3,))           # x = 0 mit den Nachfahren 1, 2, 3, 4
    assert B.backdoor_check(wide, 0, 4, (3, 1, 2)).descendants_in_z == (1, 2, 3)


def test_d_separation_module_is_the_one_of_the_previous_piece():
    parents = ((), (), (0, 1), (2,))
    assert set(G.separations(parents, None)) == {(0, 1, ()), (0, 3, (2,)), (0, 3, (1, 2)), (1, 3, (2,)), (1, 3, (0, 2))}
    assert G.local_markov_basis(parents) == [(0, 1, ()), (0, 3, (2,)), (1, 3, (2,))]
