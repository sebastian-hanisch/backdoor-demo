"""Kern: Diagramme als Elternmengen, d-Separation, Pfade mit Blockierungsgrund, Aussagenmengen, Markov-Äquivalenz.

Nur Standardbibliothek, kein numpy, kein Streamlit. Ein Diagramm ist ein Tupel von Elternmengen: `parents[j]` ist das Tupel der Eltern von Knoten j.
Jede Einheit ist eine reine Funktion. Die Entscheidung d-separiert / verbunden fällt über die Moralisierung des Vorfahren-Graphen (`d_separated`);
`explain_paths` liefert dieselbe Aussage über die Pfade und den Grund der Blockierung (Anzeige und unabhängiger Rechenweg für die Tests).
"""

from __future__ import annotations

import itertools
from collections import defaultdict
from dataclasses import dataclass

MAX_PATHS = 400


# ----------------------------------------------------------------------------- Aufbau und Grundbegriffe

def parents_from_edges(n: int, edges) -> tuple:
    """Elterntupel aus Kanten (i, j) mit i < j (feste topologische Reihenfolge, also nie ein Zyklus)."""
    parents = [[] for _ in range(n)]
    for i, j in sorted(set(edges)):
        if not (0 <= i < j < n):
            raise ValueError(f"Kante ({i}, {j}) liegt nicht in der topologischen Reihenfolge der {n} Knoten")
        parents[j].append(i)
    return tuple(tuple(p) for p in parents)


def edges_of(parents) -> tuple:
    return tuple(sorted((p, j) for j, ps in enumerate(parents) for p in ps))


def ancestors(parents, nodes) -> set:
    """Die Knoten selbst und alle ihre Vorfahren."""
    found, stack = set(nodes), list(nodes)
    while stack:
        v = stack.pop()
        for p in parents[v]:
            if p not in found:
                found.add(p)
                stack.append(p)
    return found


def descendants(parents, v: int) -> set:
    """Alle Nachfahren von v (ohne v selbst)."""
    children = defaultdict(list)
    for c, ps in enumerate(parents):
        for p in ps:
            children[p].append(c)
    found, stack = set(), [v]
    while stack:
        u = stack.pop()
        for c in children[u]:
            if c not in found:
                found.add(c)
                stack.append(c)
    return found


def is_complete(parents) -> bool:
    """Jedes Knotenpaar ist durch eine Kante verbunden: das Diagramm behauptet keine Unabhängigkeit."""
    n = len(parents)
    return len(edges_of(parents)) == n * (n - 1) // 2


# ----------------------------------------------------------------------------- d-Separation

def moral_graph(parents, keep) -> dict:
    """Ungerichteter Graph auf `keep`: jede Kante zwischen Knoten in keep, dazu eine Kante zwischen je zwei Eltern desselben Knotens."""
    adj = defaultdict(set)
    for c in keep:
        ps = [p for p in parents[c] if p in keep]
        for p in ps:
            adj[p].add(c)
            adj[c].add(p)
        for a, b in itertools.combinations(ps, 2):
            adj[a].add(b)
            adj[b].add(a)
    return adj


def d_separated(parents, x: int, y: int, z=()) -> bool:
    """x und y sind durch z d-separiert: im moralisierten Vorfahren-Graphen von {x, y} und z trennt z die beiden (Lauritzen u. a. 1990)."""
    z = set(z)
    if x in z or y in z or x == y:
        raise ValueError("x und y müssen verschieden sein und dürfen nicht zur Bedingungsmenge gehören")
    adj = moral_graph(parents, ancestors(parents, {x, y} | z))
    seen, stack = {x}, [x]
    while stack:
        u = stack.pop()
        if u == y:
            return False
        for w in adj[u]:
            if w not in seen and w not in z:
                seen.add(w)
                stack.append(w)
    return True


@dataclass(frozen=True)
class PathInfo:
    nodes: tuple          # Knotenfolge von x nach y
    arrows: tuple         # je Kante "→" (vorwärts) oder "←" (rückwärts)
    blocked: bool
    blocker: int | None   # der Knoten, der blockiert
    kind: str | None      # "bedingt" (Kette oder Gabel in z) oder "collider" (Collider und alle Nachfahren nicht in z)


def explain_paths(parents, x: int, y: int, z=()) -> list[PathInfo]:
    """Alle einfachen Pfade zwischen x und y (Kantenrichtung ignoriert) mit Blockierung nach der Pfaddefinition. Höchstens MAX_PATHS Pfade."""
    z = set(z)
    n = len(parents)
    nbrs = defaultdict(set)
    for c, ps in enumerate(parents):
        for p in ps:
            nbrs[p].add(c)
            nbrs[c].add(p)
    desc = {v: descendants(parents, v) for v in range(n)}
    out: list[PathInfo] = []

    def judge(path):
        arrows = tuple("→" if path[i] in parents[path[i + 1]] else "←" for i in range(len(path) - 1))
        for i in range(1, len(path) - 1):
            a, m, b = path[i - 1], path[i], path[i + 1]
            if a in parents[m] and b in parents[m]:
                if m not in z and not (desc[m] & z):
                    return PathInfo(tuple(path), arrows, True, m, "collider")
            elif m in z:
                return PathInfo(tuple(path), arrows, True, m, "bedingt")
        return PathInfo(tuple(path), arrows, False, None, None)

    def walk(path):
        if len(out) >= MAX_PATHS:
            return
        v = path[-1]
        if v == y:
            out.append(judge(path))
            return
        for w in sorted(nbrs[v]):
            if w not in path:
                path.append(w)
                walk(path)
                path.pop()

    walk([x])
    return out


# ----------------------------------------------------------------------------- Aussagenmengen

def separations(parents, max_cond: int | None = 2) -> list:
    """Alle d-Separationen (x < y, z) mit |z| <= max_cond (None: alle), sortiert. Jede ist eine Aussage „x und y sind unabhängig, gegeben z“."""
    n = len(parents)
    out = []
    for x, y in itertools.combinations(range(n), 2):
        rest = [v for v in range(n) if v not in (x, y)]
        top = len(rest) if max_cond is None else min(max_cond, len(rest))
        for k in range(top + 1):
            for z in itertools.combinations(rest, k):
                if d_separated(parents, x, y, z):
                    out.append((x, y, z))
    return out


def local_markov_basis(parents) -> list:
    """Lokale Markov-Basis: jeder Knoten ist von seinen Nicht-Nachfahren (ohne Eltern) unabhängig, gegeben seine Eltern. Sortiert, ohne Doppelte."""
    out = set()
    n = len(parents)
    for v in range(n):
        desc = descendants(parents, v)
        for u in range(n):
            if u != v and u not in desc and u not in parents[v]:
                out.add((min(u, v), max(u, v), tuple(sorted(parents[v]))))
    return sorted(out)


def statement_set(parents, max_cond: int | None = None) -> frozenset:
    """Menge der d-Separationen als frozenset (für Vergleiche und Äquivalenzklassen)."""
    return frozenset(separations(parents, max_cond))


# ----------------------------------------------------------------------------- Markov-Äquivalenz (nur kleine n)

def all_dags(n: int):
    """Alle gerichteten azyklischen Graphen auf n nummerierten Knoten (n <= 4) als Elterntupel."""
    if n > 4:
        raise ValueError("Aufzählung nur bis 4 Knoten")
    pairs = [(i, j) for i in range(n) for j in range(n) if i != j]
    for mask in range(1 << len(pairs)):
        parents = [[] for _ in range(n)]
        for k, (i, j) in enumerate(pairs):
            if mask >> k & 1:
                parents[j].append(i)
        if _acyclic(parents):
            yield tuple(tuple(p) for p in parents)


def _acyclic(parents) -> bool:
    n = len(parents)
    indeg = [len(p) for p in parents]
    children = defaultdict(list)
    for c, ps in enumerate(parents):
        for p in ps:
            children[p].append(c)
    stack = [v for v in range(n) if indeg[v] == 0]
    seen = 0
    while stack:
        v = stack.pop()
        seen += 1
        for c in children[v]:
            indeg[c] -= 1
            if indeg[c] == 0:
                stack.append(c)
    return seen == n


def equivalence_classes(n: int) -> dict:
    """Markov-Äquivalenzklassen aller DAGs auf n Knoten: {Aussagenmenge: Liste der DAGs}."""
    classes: dict = {}
    for parents in all_dags(n):
        classes.setdefault(statement_set(parents), []).append(parents)
    return classes
