"""Konstanten: Welten (feste Diagramme mit Koeffizienten), Regler-Grenzen, Experimente, Farben und Presets."""

# Rechenaufwand am Maximum: eine Stichprobe mit n = 5 000 und 6 Knoten, Regression mit höchstens 4 Kontrollvariablen, unter 20 ms.
N_MIN, N_MAX, N_STEP, DEFAULT_N = 100, 5000, 100, 500
SEED_MAX, DEFAULT_SEED = 999999, 35
Z_CRIT = 1.959964                                  # 95-%-Intervall, Normalnäherung (n >= 100)

# Welten: Knoten in topologischer Reihenfolge (Pfeile nur von kleinem zu großem Index). Die Daten kommen aus diesem Diagramm; Behandlung x, Wirkung y,
# die Adjustierungsmenge und unbeobachtete Knoten wählt man in der App.
WORLDS = {
    "6-Knoten-Beispiel": {
        "nodes": ("Region", "Wetter", "Schwankung", "Faktor", "Lieferverzug", "Servicegrad"),
        "coefs": {(0, 2): 0.8, (2, 3): 0.9, (0, 4): 0.7, (1, 4): 0.7, (2, 5): -0.6, (3, 5): 0.5, (4, 5): -0.8},
        "pos": ((0.0, 0.5), (0.0, 0.0), (0.33, 0.75), (0.66, 0.9), (0.4, 0.15), (1.0, 0.4)),
        "query": (3, 5, (2,), ()),
        "help": "Faktor → Servicegrad mit zwei Rückwegen über die Schwankung: Wer die Schwankung festhält, schließt beide.",
    },
    "Diagramm A (Schwankung → Faktor)": {
        "nodes": ("Schwankung", "Faktor", "Servicegrad"),
        "coefs": {(0, 1): 0.8, (0, 2): -0.6, (1, 2): 0.5},
        "pos": ((0.5, 1.0), (0.0, 0.0), (1.0, 0.0)),
        "query": (1, 2, (0,), ()),
        "help": "Das erste Diagramm aus Stück 1: ein Rückweg über die Schwankung, die Menge {Schwankung} schließt ihn.",
    },
    "Diagramm B (Faktor → Schwankung)": {
        "nodes": ("Faktor", "Schwankung", "Servicegrad"),
        "coefs": {(0, 1): 0.8, (1, 2): 0.4, (0, 2): 0.5},
        "pos": ((0.0, 0.0), (0.5, 1.0), (1.0, 0.0)),
        "query": (0, 2, (1,), ()),
        "help": "Das zweite Diagramm aus Stück 1: kein Rückweg, die Schwankung ist ein Nachfahre des Faktors. Dieselbe Menge ist hier ungültig.",
    },
    "Mediator-Welt": {
        "nodes": ("Schwankung", "Faktor", "Bestand", "Servicegrad"),
        "coefs": {(0, 1): 0.8, (0, 3): -0.6, (1, 2): 0.5, (2, 3): 0.8, (1, 3): 0.3},
        "pos": ((0.0, 1.0), (0.0, 0.0), (0.5, 0.0), (1.0, 0.5)),
        "query": (1, 3, (0, 2), ()),
        "help": "Der Faktor wirkt direkt (0,3) und über den Bestand (0,5 · 0,8). Alles kontrollieren rechnet den Umweg weg.",
    },
}
WORLD_ORDER = tuple(WORLDS)
DEFAULT_WORLD = "6-Knoten-Beispiel"

# Experimente: feste Ströme (Seeds aus SEED_BASE), nie ein einzelner Seed als Befund.
SEED_BASE = 900000
EXP_SETS_N, EXP_SETS_REPS = 500, 300              # Experiment 1: alle Mengen der 6-Knoten-Welt
EXP_RECIPE_DIAGRAMS = 600                         # Experiment 2: Zufallsdiagramme mit 6 Knoten
EXP_CRITERION_DIAGRAMS = 400                      # Experiment 3: Zufallsdiagramme mit 6 Knoten, alle 16 Mengen
EXP_HIDDEN_DIAGRAMS = 800                         # Experiment 4: Zufallsdiagramme mit 7 Knoten, ein verborgener Knoten
RANDOM_NODES, RANDOM_NODES_HIDDEN = 6, 7
RANDOM_P_LO, RANDOM_P_HI = 0.3, 0.6
COEF_LO, COEF_HI = 0.4, 1.2
TOL = 1e-8                                         # "Koeffizient richtig" in der Population

COLOR_CAUSAL = "#2F6B65"
COLOR_OPEN = "#D68A2E"
COLOR_BLOCKED = "#a9a9a9"
COLOR_EDGE = "#6b6b6b"
COLOR_COND = "#4c78a8"
COLOR_FORBIDDEN = "#c0392b"
COLOR_HIDDEN = "#cfcfcf"


def preset(world: str, n: int = DEFAULT_N) -> dict:
    x, y, z, hidden = WORLDS[world]["query"]
    return {"world": world, "x": x, "y": y, "z": z, "hidden": hidden, "n": n, "seed": DEFAULT_SEED}


PRESETS = {
    "6-Knoten-Beispiel (Voreinstellung)": preset("6-Knoten-Beispiel"),
    "Diagramm A": preset("Diagramm A (Schwankung → Faktor)"),
    "Diagramm B": preset("Diagramm B (Faktor → Schwankung)"),
    "Alles kontrollieren schadet": preset("Mediator-Welt"),
    "Eine Variable fehlt": {"world": "6-Knoten-Beispiel", "x": 3, "y": 5, "z": (4,), "hidden": (2,), "n": DEFAULT_N, "seed": DEFAULT_SEED},
}
PRESET_HELP = {
    "6-Knoten-Beispiel (Voreinstellung)": WORLDS["6-Knoten-Beispiel"]["help"],
    "Diagramm A": WORLDS["Diagramm A (Schwankung → Faktor)"]["help"],
    "Diagramm B": WORLDS["Diagramm B (Faktor → Schwankung)"]["help"],
    "Alles kontrollieren schadet": WORLDS["Mediator-Welt"]["help"],
    "Eine Variable fehlt": "Die Schwankung ist nicht beobachtet: Beide Rückwege laufen über sie, und unter den übrigen Variablen gibt es keine gültige Menge.",
}
