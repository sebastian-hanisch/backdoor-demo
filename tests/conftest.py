"""Gemeinsame Fixtures: die Mini-Instanzen, an denen jede Einheit von Hand geprüft wird (DEMO-PLAYBOOK §1b)."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def confounded():
    """Mini-Instanz 1 (0 = Z, 1 = X, 2 = Y): Z -> X (1), Z -> Y (−1), X -> Y (2), Einheitsrauschen.
    Handrechnung: Var(X) = 2, Cov(X, Y) = (−1)(1) + 2·2 = 3. Koeffizient ohne Z: 3/2 = 1,5; mit Z: 2 (= wahre Wirkung).
    Backdoor: leere Menge ungültig (Rückweg X <- Z -> Y), {Z} gültig."""
    parents = ((), (0,), (0, 1))
    b = np.zeros((3, 3))
    b[1, 0], b[2, 0], b[2, 1] = 1.0, -1.0, 2.0
    return parents, b


@pytest.fixture
def mediator():
    """Mini-Instanz 2 (0 = Z, 1 = X, 2 = B, 3 = Y): Z -> X (1), Z -> Y (−1), X -> B (0,5), B -> Y (0,8), X -> Y (0,3).
    Gesamtwirkung 0,3 + 0,5·0,8 = 0,7. Koeffizient mit {Z}: 0,7 (gültig); ohne Menge: 0,2; mit {B}: −0,2; mit {Z, B}: 0,3 (nur direkt, ungültig)."""
    parents = ((), (0,), (1,), (0, 1, 2))
    b = np.zeros((4, 4))
    b[1, 0], b[3, 0], b[2, 1], b[3, 2], b[3, 1] = 1.0, -1.0, 0.5, 0.8, 0.3
    return parents, b
