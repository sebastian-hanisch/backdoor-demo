"""Kern: Rückwege, Backdoor-Kriterium (Pearl), Adjustierungskriterium (Shpitser/VanderWeele/Robins), gültige Mengen und Standardrezepte.

Nur Standardbibliothek und `dsep_graph` (wortgleich aus d-separation-demo), kein Streamlit. Diagramm = Tupel von Elternmengen. Jede Einheit eine reine Funktion.
Das Backdoor-Kriterium läuft über die Pfade mit Blockierungsgrund (`dsep_graph.explain_paths`); der Graph ohne die von x ausgehenden Kanten ist der zweite
Rechenweg (nur im Test).
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

import dsep_graph as G


def directed_paths(parents, x: int, y: int) -> list[tuple]:
    """Alle gerichteten Pfade x → … → y als Knotenfolgen (die kausalen Pfade)."""
    children = {v: [] for v in range(len(parents))}
    for c, ps in enumerate(parents):
        for p in ps:
            children[p].append(c)
    out: list[tuple] = []

    def walk(path):
        v = path[-1]
        if v == y:
            out.append(tuple(path))
            return
        for c in sorted(children[v]):
            path.append(c)
            walk(path)
            path.pop()

    walk([x])
    return out


def backdoor_paths(parents, x: int, y: int, z=()) -> list[G.PathInfo]:
    """Alle Pfade zwischen x und y, deren erste Kante in x hineinführt (Rückwege), mit Blockierung durch z."""
    return [p for p in G.explain_paths(parents, x, y, z) if p.arrows and p.arrows[0] == "←"]


@dataclass(frozen=True)
class BackdoorResult:
    valid: bool
    descendants_in_z: tuple     # Knoten in z, die Nachfahren von x sind (verboten)
    open_paths: tuple           # offene Rückwege (PathInfo)
    blocked_paths: tuple        # blockierte Rückwege (PathInfo)


def backdoor_check(parents, x: int, y: int, z=()) -> BackdoorResult:
    """Backdoor-Kriterium: z enthält keinen Nachfahren von x und blockiert jeden Rückweg."""
    z = tuple(sorted(set(z)))
    if x in z or y in z or x == y:
        raise ValueError("x und y müssen verschieden sein und dürfen nicht in z liegen")
    forbidden = tuple(v for v in z if v in G.descendants(parents, x))
    paths = backdoor_paths(parents, x, y, z)
    open_paths = tuple(p for p in paths if not p.blocked)
    blocked_paths = tuple(p for p in paths if p.blocked)
    return BackdoorResult(valid=not forbidden and not open_paths, descendants_in_z=forbidden, open_paths=open_paths, blocked_paths=blocked_paths)


def backdoor_valid(parents, x: int, y: int, z=()) -> bool:
    return backdoor_check(parents, x, y, z).valid


def forbidden_nodes(parents, x: int, y: int) -> set:
    """Verbotene Knoten des Adjustierungskriteriums: die Knoten auf kausalen Pfaden (ohne x) und ihre Nachfahren."""
    on_path = {v for p in directed_paths(parents, x, y) for v in p[1:]}
    forb = set(on_path)
    for v in on_path:
        forb |= G.descendants(parents, v)
    return forb


def adjustment_valid(parents, x: int, y: int, z=()) -> bool:
    """Adjustierungskriterium: keine verbotenen Knoten in z, und x und y sind durch z getrennt im Graphen, in dem die ersten Kanten der kausalen Pfade fehlen.
    Allgemeiner als das Backdoor-Kriterium: auch Nachfahren von x sind erlaubt, wenn sie auf keinem kausalen Pfad liegen und keine Verzerrung öffnen."""
    z = set(z)
    if x in z or y in z or x == y:
        raise ValueError("x und y müssen verschieden sein und dürfen nicht in z liegen")
    if z & forbidden_nodes(parents, x, y):
        return False
    first = {p[1] for p in directed_paths(parents, x, y)}
    cut = tuple(tuple(q for q in ps if not (q == x and c in first)) for c, ps in enumerate(parents))
    return G.d_separated(cut, x, y, z)


def all_sets(candidates) -> list[tuple]:
    """Alle Teilmengen der Kandidaten, nach Größe und Nummer sortiert."""
    items = sorted(candidates)
    return [c for k in range(len(items) + 1) for c in itertools.combinations(items, k)]


def valid_sets(parents, x: int, y: int, candidates, criterion: str = "backdoor") -> list[tuple]:
    """Alle gültigen Mengen unter den beobachteten Kandidaten (ohne x und y)."""
    check = backdoor_valid if criterion == "backdoor" else adjustment_valid
    return [z for z in all_sets([v for v in candidates if v not in (x, y)]) if check(parents, x, y, z)]


def minimal_sets(sets) -> list[tuple]:
    """Die inklusionsminimalen unter den Mengen."""
    sets = [frozenset(s) for s in sets]
    return [tuple(sorted(s)) for s in sets if not any(t < s for t in sets)]


def standard_recipes(parents, x: int, y: int) -> dict:
    """Die gängigen Rezepte als Mengen: nichts, alles andere, Eltern von x, alle Nicht-Nachfahren von x, alle Vorfahren von y."""
    n = len(parents)
    others = [v for v in range(n) if v not in (x, y)]
    desc = G.descendants(parents, x)
    anc_y = G.ancestors(parents, {y})
    return {
        "leere Menge": (),
        "alle anderen Variablen": tuple(others),
        "Eltern von x": tuple(sorted(v for v in parents[x] if v != y)),
        "alle Nicht-Nachfahren von x": tuple(v for v in others if v not in desc),
        "alle Vorfahren von y": tuple(v for v in others if v in anc_y),
    }
