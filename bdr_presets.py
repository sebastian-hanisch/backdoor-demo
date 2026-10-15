"""Permalink (Begrenzen), Presets, Zustandsbereinigung und Zufalls-Seed-Button (Standardmuster aus dem Demo-Portfolio).

Alle Regler sind in jeder Einstellung wirksam und werden immer gezeichnet. Berechnete Auswahllisten (Knoten) hängen von der Welt und von x, y und den
unbeobachteten Knoten ab; deshalb bereinigt `clean_state` vor dem Zeichnen jeden gespeicherten Wert, der in der aktuellen Auswahl nicht vorkommt.
"""

import random

import streamlit as st

import bdr_constants as C


def n_nodes(world: str) -> int:
    return len(C.WORLDS[world]["nodes"])


def init_session_state_defaults():
    p = C.PRESETS["6-Knoten-Beispiel (Voreinstellung)"]
    defaults = {"world_select": p["world"], "x_select": p["x"], "y_select": p["y"], "z_select": list(p["z"]), "hidden_select": list(p["hidden"]),
                "n_slider": p["n"], "seed_input": p["seed"]}
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def bounds(key):
    return {"n_slider": (C.N_MIN, C.N_MAX), "seed_input": (0, C.SEED_MAX)}[key]


def clean_state():
    """Vor dem Zeichnen der Regler: nur Werte behalten, die in der aktuellen Welt gültig sind (Welt, x, y, unbeobachtete Knoten, Menge)."""
    ss = st.session_state
    if ss.get("world_select") not in C.WORLDS:
        ss["world_select"] = C.DEFAULT_WORLD
    n = n_nodes(ss["world_select"])
    x = ss.get("x_select", 0)
    x = x if isinstance(x, int) and 0 <= x < n else 0
    y = ss.get("y_select", n - 1)
    y = y if isinstance(y, int) and 0 <= y < n and y != x else next(v for v in reversed(range(n)) if v != x)
    ss["x_select"], ss["y_select"] = x, y
    hidden = [v for v in ss.get("hidden_select", []) if isinstance(v, int) and 0 <= v < n and v not in (x, y)]
    ss["hidden_select"] = hidden
    ss["z_select"] = [v for v in ss.get("z_select", []) if isinstance(v, int) and 0 <= v < n and v not in (x, y) and v not in hidden]
    ss["n_slider"] = min(C.N_MAX, max(C.N_MIN, int(ss.get("n_slider", C.DEFAULT_N))))


def load_permalink_settings():
    """Einmal je Sitzung: Werte aus der Adresszeile übernehmen; ungültige Werte werden von `clean_state` bereinigt."""
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    init_session_state_defaults()
    ss = st.session_state

    def ints(text):
        return [int(t) for t in text.split(",") if t.strip().lstrip("-").isdigit()]

    if "w" in qp and qp["w"] in C.WORLDS:
        ss["world_select"] = qp["w"]
        x, y, z, h = C.WORLDS[qp["w"]]["query"]
        ss["x_select"], ss["y_select"], ss["z_select"], ss["hidden_select"] = x, y, list(z), list(h)
    try:
        if "x" in qp:
            ss["x_select"] = int(qp["x"])
        if "y" in qp:
            ss["y_select"] = int(qp["y"])
        if "z" in qp:
            ss["z_select"] = ints(qp["z"])
        if "h" in qp:
            ss["hidden_select"] = ints(qp["h"])
        if "n" in qp:
            ss["n_slider"] = int(qp["n"])
        if "seed" in qp:
            ss["seed_input"] = max(0, min(C.SEED_MAX, int(qp["seed"])))
    except (ValueError, TypeError):
        pass
    ss["permalink_loaded"] = True


def sync_query_params(values: dict):
    """`values`: Parameter -> Text; die Adresszeile spiegelt die Konfiguration."""
    try:
        for key, value in values.items():
            st.query_params[key] = str(value)
    except Exception:
        pass


def apply_preset(name):
    p = C.PRESETS[name]
    ss = st.session_state
    ss["world_select"] = p["world"]
    ss["x_select"], ss["y_select"], ss["z_select"], ss["hidden_select"] = p["x"], p["y"], list(p["z"]), list(p["hidden"])
    ss["n_slider"], ss["seed_input"] = p["n"], p["seed"]


def on_world_change():
    """Neue Welt: Behandlung, Wirkung, Menge und unbeobachtete Knoten auf die Voreinstellung der Welt."""
    x, y, z, h = C.WORLDS[st.session_state["world_select"]]["query"]
    st.session_state["x_select"], st.session_state["y_select"] = x, y
    st.session_state["z_select"], st.session_state["hidden_select"] = list(z), list(h)


def randomize_seed():
    st.session_state["seed_input"] = random.randint(0, C.SEED_MAX)
