"""Auswertung: Schätzung mit einer Adjustierungsmenge, Urteil der Kriterien, die vier Experimente über feste Ströme und die Verdikte. Nur numpy."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

import bdr_backdoor as B
import bdr_constants as C
import dsep_graph as G
from kausal_generator import Scm, SplitMix64, coefficient_matrix, sample, total_effect


def de(x: float, digits: int = 2) -> str:
    """Zahl mit deutschem Dezimalkomma und typografischem Minuszeichen."""
    return f"{x:.{digits}f}".replace(".", ",").replace("-", "−")


def signed(x: float, digits: int = 2) -> str:
    return ("+" if x >= 0 else "−") + de(abs(x), digits)


# ----------------------------------------------------------------------------- Welten, Population, Schätzer

def world_scm(world: str) -> Scm:
    """Lineares Strukturmodell der Welt (Rauschen N(0,1) in jedem Knoten)."""
    w = C.WORLDS[world]
    n = len(w["nodes"])
    parents = G.parents_from_edges(n, w["coefs"])
    return Scm(names=w["nodes"], parents=parents, coefs=tuple(tuple(w["coefs"][(p, j)] for p in parents[j]) for j in range(n)),
               intercepts=(0.0,) * n, noise_sd=(1.0,) * n, binary=(False,) * n)


def true_parents(world: str) -> tuple:
    return G.parents_from_edges(len(C.WORLDS[world]["nodes"]), C.WORLDS[world]["coefs"])


def population(b: np.ndarray):
    """Kovarianz Σ = (I − B)⁻¹(I − B)⁻ᵀ und Gesamtwirkungen T[j, i] = (I − B)⁻¹ − I bei Einheitsrauschen."""
    inv = np.linalg.inv(np.eye(len(b)) - b)
    return inv @ inv.T, inv - np.eye(len(b))


def population_coefficient(cov: np.ndarray, x: int, y: int, z=()) -> float:
    """Koeffizient von x in der Regression von y auf x und z in der Population."""
    idx = [x] + list(z)
    return float(np.linalg.solve(cov[np.ix_(idx, idx)], cov[idx, y])[0])


def ols_coefficient(y: np.ndarray, x: np.ndarray, zs=()) -> tuple[np.ndarray, np.ndarray]:
    """Koeffizient von x und Standardfehler in y ~ 1 + x + zs (kleinste Quadrate), je Wiederholung (Zeilen). Eingaben (reps, n)."""
    reps, n = y.shape
    cols = [np.ones_like(y), x] + list(zs)
    design = np.stack(cols, axis=2)                                    # (reps, n, k)
    xtx = np.einsum("rni,rnj->rij", design, design)
    xty = np.einsum("rni,rn->ri", design, y)
    beta = np.linalg.solve(xtx, xty[..., None])[..., 0]
    resid = y - np.einsum("rni,ri->rn", design, beta)
    s2 = (resid ** 2).sum(axis=1) / (n - design.shape[2])
    se = np.sqrt(s2 * np.linalg.inv(xtx)[:, 1, 1])
    return beta[:, 1], se


def covers(estimate, se, truth: float):
    return np.abs(np.asarray(estimate) - truth) <= C.Z_CRIT * np.asarray(se)


def random_dag(n: int, p: float, rng: SplitMix64) -> tuple:
    """Zufälliges Diagramm in der Knotenreihenfolge 0..n-1 mit Kantenwahrscheinlichkeit p (ein Block Gleichverteilte, feste Reihenfolge)."""
    u = rng.uniform(n * (n - 1) // 2)
    k = 0
    parents = []
    for j in range(n):
        ps = []
        for i in range(j):
            if u[k] < p:
                ps.append(i)
            k += 1
        parents.append(tuple(ps))
    return tuple(parents)


def random_coefficients(parents, rng: SplitMix64) -> np.ndarray:
    n = len(parents)
    u = rng.uniform(2 * n * n)
    b = np.zeros((n, n))
    k = 0
    for c, ps in enumerate(parents):
        for p in ps:
            sign = 1.0 if u[k] < 0.5 else -1.0
            b[c, p] = sign * (C.COEF_LO + (C.COEF_HI - C.COEF_LO) * u[k + 1])
            k += 2
    return b


# ----------------------------------------------------------------------------- Auswertung der Einstellungen

@dataclass(frozen=True)
class Settings:
    world: str = C.DEFAULT_WORLD
    x: int = 3
    y: int = 5
    z: tuple = (2,)
    hidden: tuple = ()
    n: int = C.DEFAULT_N
    seed: int = C.DEFAULT_SEED


@dataclass
class SetRow:
    z: tuple
    backdoor: bool
    adjustment: bool
    bias: float            # Koeffizient in der Population minus Wahrheit


@dataclass
class Analysis:
    settings: Settings
    names: tuple
    parents: tuple
    check: B.BackdoorResult
    adjustment: bool
    causal_paths: list
    truth: float
    pop_coef: float
    estimate: float
    se: float
    lo: float
    hi: float
    covers: bool
    rows: list
    candidates: tuple
    no_valid_set: bool
    n_valid: int


def observed_candidates(n_nodes: int, x: int, y: int, hidden) -> tuple:
    return tuple(v for v in range(n_nodes) if v not in (x, y) and v not in set(hidden))


def analyse(s: Settings) -> Analysis:
    scm = world_scm(s.world)
    parents = scm.parents
    n_nodes = len(parents)
    z = tuple(sorted(s.z))
    cov, total = population(coefficient_matrix(scm))
    truth = total_effect(scm, scm.names[s.x], scm.names[s.y])
    d = sample(scm, s.n, SplitMix64(s.seed))
    yv, xv = d[scm.names[s.y]], d[scm.names[s.x]]
    est, se = ols_coefficient(yv, xv, [d[scm.names[v]] for v in z])
    est, se = float(est[0]), float(se[0])
    cands = observed_candidates(n_nodes, s.x, s.y, s.hidden)
    rows = [SetRow(zz, B.backdoor_valid(parents, s.x, s.y, zz), B.adjustment_valid(parents, s.x, s.y, zz),
                   population_coefficient(cov, s.x, s.y, zz) - truth) for zz in B.all_sets(cands)]
    return Analysis(
        settings=s, names=scm.names, parents=parents, check=B.backdoor_check(parents, s.x, s.y, z), adjustment=B.adjustment_valid(parents, s.x, s.y, z),
        causal_paths=B.directed_paths(parents, s.x, s.y), truth=truth, pop_coef=population_coefficient(cov, s.x, s.y, z), estimate=est, se=se,
        lo=est - C.Z_CRIT * se, hi=est + C.Z_CRIT * se, covers=bool(abs(est - truth) <= C.Z_CRIT * se), rows=rows, candidates=cands,
        no_valid_set=not any(r.backdoor for r in rows), n_valid=sum(r.backdoor for r in rows),
    )


# ----------------------------------------------------------------------------- Experiment 1: alle Mengen der 6-Knoten-Welt

def sets_experiment(n: int = C.EXP_SETS_N, reps: int = C.EXP_SETS_REPS) -> list[dict]:
    scm = world_scm("6-Knoten-Beispiel")
    x, y = 3, 5
    cov, total = population(coefficient_matrix(scm))
    truth = float(total[y, x])
    d = sample(scm, n, SplitMix64(C.SEED_BASE + 1), reps)
    names = scm.names
    rows = []
    for z in B.all_sets([0, 1, 2, 4]):
        est, se = ols_coefficient(d[names[y]], d[names[x]], [d[names[v]] for v in z])
        rows.append({"z": z, "names": tuple(names[v] for v in z), "valid": B.backdoor_valid(scm.parents, x, y, z), "adj": B.adjustment_valid(scm.parents, x, y, z),
                     "bias": population_coefficient(cov, x, y, z) - truth, "mean": float(est.mean()), "cover": float(covers(est, se, truth).mean())})
    return rows


# ----------------------------------------------------------------------------- Experiment 2: Standardrezepte

def recipes_experiment(diagrams: int = C.EXP_RECIPE_DIAGRAMS) -> dict:
    rng = SplitMix64(C.SEED_BASE + 2)
    out = {"all": {}, "with_parent": {}, "n_all": 0, "n_parent": 0, "valid_counts": [], "min_sizes": []}
    for key in ("all", "with_parent"):
        for name in B.standard_recipes(((), (0,)), 0, 1):
            out[key][name] = 0
    while out["n_all"] < diagrams:
        parents = random_dag(C.RANDOM_NODES, C.RANDOM_P_LO + (C.RANDOM_P_HI - C.RANDOM_P_LO) * float(rng.uniform(1)[0]), rng)
        pair = rng.uniform(2)
        x = int(pair[0] * C.RANDOM_NODES)
        y = int(pair[1] * C.RANDOM_NODES)
        if x >= y or not B.directed_paths(parents, x, y):
            continue
        out["n_all"] += 1
        recipes = B.standard_recipes(parents, x, y)
        ok = {name: B.backdoor_valid(parents, x, y, z) for name, z in recipes.items()}
        for name, v in ok.items():
            out["all"][name] += v
        if parents[x]:
            out["n_parent"] += 1
            for name, v in ok.items():
                out["with_parent"][name] += v
        valid = B.valid_sets(parents, x, y, range(C.RANDOM_NODES))
        out["valid_counts"].append(len(valid))
        out["min_sizes"].append(min(len(z) for z in valid))
    return out


# ----------------------------------------------------------------------------- Experiment 3: das Kriterium gegen die Wahrheit

def criterion_experiment(diagrams: int = C.EXP_CRITERION_DIAGRAMS) -> dict:
    rng = SplitMix64(C.SEED_BASE + 3)
    cnt = {"valid_correct": 0, "valid_wrong": 0, "invalid_correct": 0, "invalid_wrong": 0, "adj_disagree": 0, "pairs": 0, "diagrams": 0}
    while cnt["diagrams"] < diagrams:
        n = C.RANDOM_NODES
        parents = random_dag(n, C.RANDOM_P_LO + (C.RANDOM_P_HI - C.RANDOM_P_LO) * float(rng.uniform(1)[0]), rng)
        pair = rng.uniform(2)
        x, y = int(pair[0] * n), int(pair[1] * n)
        if x >= y:
            continue
        b = random_coefficients(parents, rng)
        cov, total = population(b)
        truth = float(total[y, x])
        cnt["diagrams"] += 1
        for z in B.all_sets([v for v in range(n) if v not in (x, y)]):
            bd = B.backdoor_valid(parents, x, y, z)
            adj = B.adjustment_valid(parents, x, y, z)
            correct = abs(population_coefficient(cov, x, y, z) - truth) < C.TOL
            cnt["pairs"] += 1
            cnt[("valid_" if bd else "invalid_") + ("correct" if correct else "wrong")] += 1
            cnt["adj_disagree"] += adj != correct
    return cnt


# ----------------------------------------------------------------------------- Experiment 4: eine Variable fehlt

def hidden_experiment(diagrams: int = C.EXP_HIDDEN_DIAGRAMS) -> dict:
    rng = SplitMix64(C.SEED_BASE + 4)
    n = C.RANDOM_NODES_HIDDEN
    counts = {"common": [0, 0], "other": [0, 0]}          # [Fälle, ohne gültige beobachtete Menge]
    done = 0
    while done < diagrams:
        parents = random_dag(n, 0.25 + 0.25 * float(rng.uniform(1)[0]), rng)
        pair = rng.uniform(3)
        x, y = int(pair[0] * n), int(pair[1] * n)
        if x >= y or not B.directed_paths(parents, x, y):
            continue
        others = [v for v in range(n) if v not in (x, y)]
        h = others[int(pair[2] * len(others))]
        done += 1
        obs = [v for v in others if v != h]
        exists = bool(B.valid_sets(parents, x, y, obs))
        kind = "common" if (h in G.ancestors(parents, {x}) and h in G.ancestors(parents, {y})) else "other"
        counts[kind][0] += 1
        counts[kind][1] += not exists
    return counts


# ----------------------------------------------------------------------------- Verdikte: (Art, Text)

def _names(names, nodes) -> str:
    return ", ".join(names[v] for v in nodes) if nodes else "keine Variable"


def verdict_instance(a: Analysis) -> tuple[str, str]:
    s, names = a.settings, a.names
    given = _names(names, tuple(sorted(s.z)))
    if a.check.valid:
        return "success", (f"Die Menge ({given}) ist **gültig**: Sie enthält keinen Nachfahren von {names[s.x]} und blockiert "
                           f"{'alle ' + str(len(a.check.blocked_paths)) + ' Rückwege' if a.check.blocked_paths else 'jeden Rückweg (es gibt keinen)'}. "
                           f"Der Koeffizient von {names[s.x]} schätzt die Wirkung auf {names[s.y]}.")
    reasons = []
    if a.check.descendants_in_z:
        reasons.append(f"{_names(names, a.check.descendants_in_z)} {'ist ein Nachfahre' if len(a.check.descendants_in_z) == 1 else 'sind Nachfahren'} von {names[s.x]}")
    if a.check.open_paths:
        reasons.append(f"{len(a.check.open_paths)} Rückweg{'e' if len(a.check.open_paths) > 1 else ''} bleibt offen")
    text = f"Die Menge ({given}) ist nach dem Backdoor-Kriterium **ungültig**: " + " und ".join(reasons) + "."
    if a.adjustment:
        return "info", text + " Das allgemeinere Adjustierungskriterium erlaubt sie dennoch; der Koeffizient trifft die Wirkung."
    return "warning", text + " Der Koeffizient von " + names[s.x] + " trifft die Wirkung im Allgemeinen nicht."


def verdict_no_valid_set(a: Analysis) -> tuple[str, str] | None:
    if not a.no_valid_set:
        return None
    return "warning", (f"Unter den beobachteten Variablen gibt es **keine gültige Menge**: Ein Rückweg läuft über unbeobachtete Variablen und lässt sich nicht "
                       f"blockieren. Mit Adjustierung allein ist die Wirkung hier nicht zu bekommen.")


def verdict_sets(rows: list) -> tuple[str, str]:
    valid = [r for r in rows if r["valid"]]
    invalid = [r for r in rows if not r["valid"]]
    return "info", (f"{len(valid)} von {len(rows)} Mengen sind gültig, im Mittel mit einer Deckung von {de(100 * np.mean([r['cover'] for r in valid]), 1)} %; "
                    f"die {len(invalid)} ungültigen decken die Wahrheit in {de(100 * np.mean([r['cover'] for r in invalid]), 1)} % der Wiederholungen.")


def verdict_recipes(res: dict) -> tuple[str, str]:
    a = res["all"]["alle anderen Variablen"] / res["n_all"]
    b = res["with_parent"]["alle anderen Variablen"] / res["n_parent"]
    return "warning", (f"„Alle anderen Variablen kontrollieren“ ist nur in {de(100 * a, 0)} % der Zufallsdiagramme gültig ({de(100 * b, 0)} %, wenn x einen Elternknoten hat); "
                       "die Eltern von x oder alle Nicht-Nachfahren sind es immer.")


def verdict_criterion(c: dict) -> tuple[str, str]:
    valid = c["valid_correct"] + c["valid_wrong"]
    return "success", (f"Von {valid} gültigen Mengen treffen {c['valid_correct']} die Wirkung ({c['valid_wrong']} Ausnahmen). Das Kriterium ist hinreichend, "
                       f"aber nicht notwendig: {c['invalid_correct']} ungültige Mengen treffen sie trotzdem; das Adjustierungskriterium weicht in {c['adj_disagree']} "
                       f"von {c['pairs']} Paaren ab.")


def verdict_hidden(h: dict) -> tuple[str, str]:
    cases, none = h["common"]
    return "warning", (f"Ist die fehlende Variable ein Vorfahr von x (auch ein Vorfahr, der nur über x auf y wirkt), gibt es in {de(100 * none / max(cases, 1), 0)} % von {cases} Fällen keine gültige "
                       f"beobachtete Menge; in den übrigen {h['other'][0]} Fällen in {de(100 * h['other'][1] / max(h['other'][0], 1), 0)} %.")
