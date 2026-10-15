"""Orakel: Kriterien gegen einen unabhängigen Rechenweg (Graph ohne Ausgangskanten, networkx) und gegen die Wahrheit der Population. Unter zehn Sekunden."""

import itertools

import numpy as np
import pytest

nx = pytest.importorskip("networkx")

import bdr_backdoor as B  # noqa: E402
import bdr_constants as C  # noqa: E402
import bdr_evaluation as ev  # noqa: E402
import dsep_graph as G  # noqa: E402
from kausal_generator import SplitMix64, coefficient_matrix, sample, total_effect  # noqa: E402


def surgery_valid(parents, x, y, z):
    """Zweiter Rechenweg: keine Nachfahren von x in z, und x, y sind im Graphen ohne die von x ausgehenden Kanten durch z d-getrennt (networkx)."""
    if set(z) & G.descendants(parents, x):
        return False
    g = nx.DiGraph()
    g.add_nodes_from(range(len(parents)))
    g.add_edges_from((p, c) for c, ps in enumerate(parents) for p in ps if p != x)
    return bool(nx.is_d_separator(g, {x}, {y}, set(z)))


def test_backdoor_criterion_against_the_graph_surgery_on_all_small_diagrams():
    for n in (3, 4):
        for parents in G.all_dags(n):
            for x, y in itertools.permutations(range(n), 2):
                others = [v for v in range(n) if v not in (x, y)]
                for z in B.all_sets(others):
                    assert B.backdoor_valid(parents, x, y, z) == surgery_valid(parents, x, y, z), (parents, x, y, z)


def test_backdoor_criterion_against_the_graph_surgery_on_random_diagrams():
    rng = SplitMix64(9)
    for _ in range(250):
        parents = ev.random_dag(6, 0.2 + 0.4 * float(rng.uniform(1)[0]), rng)
        u = rng.uniform(2)
        x, y = int(u[0] * 6), int(u[1] * 6)
        if x == y:
            continue
        others = [v for v in range(6) if v not in (x, y)]
        for z in B.all_sets(others):
            assert B.backdoor_valid(parents, x, y, z) == surgery_valid(parents, x, y, z)


def _populations(count, seed, nodes=6):
    rng = SplitMix64(seed)
    for _ in range(count):
        parents = ev.random_dag(nodes, 0.3 + 0.3 * float(rng.uniform(1)[0]), rng)
        u = rng.uniform(2)
        x, y = int(u[0] * nodes), int(u[1] * nodes)
        if x == y:
            continue
        b = ev.random_coefficients(parents, rng)
        cov, total = ev.population(b)
        yield parents, x, y, cov, float(total[y, x])


def test_valid_sets_always_recover_the_total_effect_and_the_adjustment_criterion_is_exact():
    valid = invalid_correct = checked = 0
    for parents, x, y, cov, truth in _populations(300, 11):
        for z in B.all_sets([v for v in range(6) if v not in (x, y)]):
            correct = abs(ev.population_coefficient(cov, x, y, z) - truth) < C.TOL
            if B.backdoor_valid(parents, x, y, z):
                assert correct
                valid += 1
            elif correct:
                invalid_correct += 1
            assert B.adjustment_valid(parents, x, y, z) == correct
            checked += 1
    assert valid > 500 and invalid_correct > 100 and checked > 3000


def test_invalid_sets_are_wrong_for_generic_coefficients_unless_the_adjustment_criterion_allows_them():
    wrong = 0
    for parents, x, y, cov, truth in _populations(150, 12):
        for z in B.all_sets([v for v in range(6) if v not in (x, y)]):
            if not B.adjustment_valid(parents, x, y, z):
                assert abs(ev.population_coefficient(cov, x, y, z) - truth) > 1e-8
                wrong += 1
    assert wrong > 500


def test_a_faithfulness_violation_gives_the_right_number_for_an_invalid_set():
    """Der Pfeil z -> y ist im Diagramm, hat aber den Koeffizienten 0 (nicht generisch). Das Kriterium nennt die leere Menge ungültig; der Koeffizient ist trotzdem
    richtig. Das Kriterium bezieht sich auf das Diagramm, nicht auf zufällig passende Zahlen."""
    parents = ((), (0,), (0, 1))                       # 0 = z, 1 = x, 2 = y
    b = np.zeros((3, 3))
    b[1, 0], b[2, 0], b[2, 1] = 1.0, 0.0, 2.0
    cov, total = ev.population(b)
    assert not B.backdoor_valid(parents, 1, 2, ()) and B.backdoor_valid(parents, 1, 2, (0,))
    assert ev.population_coefficient(cov, 1, 2, ()) == pytest.approx(float(total[2, 1]))
    b[2, 0] = -1.0
    cov, total = ev.population(b)
    assert ev.population_coefficient(cov, 1, 2, ()) != pytest.approx(float(total[2, 1]), abs=0.1)


def test_total_effect_of_the_generator_equals_the_simulated_intervention_and_the_valid_regression():
    scm = ev.world_scm("6-Knoten-Beispiel")
    x, y = 3, 5
    truth = total_effect(scm, scm.names[x], scm.names[y])
    one = sample(scm, 300, SplitMix64(4), do={scm.names[x]: 1.0})[scm.names[y]]
    zero = sample(scm, 300, SplitMix64(4), do={scm.names[x]: 0.0})[scm.names[y]]
    assert truth == pytest.approx(0.5) and (one - zero).mean() == pytest.approx(truth, abs=1e-9)
    cov, _ = ev.population(coefficient_matrix(scm))
    assert ev.population_coefficient(cov, x, y, (2,)) == pytest.approx(truth, abs=1e-9)
    assert ev.population_coefficient(cov, x, y, ()) != pytest.approx(truth, abs=1e-3)


def test_regression_coefficient_against_numpy_lstsq():
    scm = ev.world_scm("Mediator-Welt")
    d = sample(scm, 400, SplitMix64(8), reps=3)
    names = scm.names
    est, se = ev.ols_coefficient(d[names[3]], d[names[1]], [d[names[0]]])
    for r in range(3):
        design = np.column_stack([np.ones(400), d[names[1]][r], d[names[0]][r]])
        coef, res, *_ = np.linalg.lstsq(design, d[names[3]][r], rcond=None)
        assert est[r] == pytest.approx(coef[1], rel=1e-9)
        sigma2 = res[0] / (400 - 3)
        assert se[r] == pytest.approx(np.sqrt(sigma2 * np.linalg.inv(design.T @ design)[1, 1]), rel=1e-9)
