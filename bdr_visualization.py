"""Plotly-Figuren und Tabellen. Alle Achsen fest (fixedrange), damit Touch-Scrollen nicht am Diagramm hängen bleibt."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

import bdr_constants as C
import dsep_graph as G
from bdr_evaluation import Analysis, de, signed

NODE_SIZE = 64


def _fixed(fig: go.Figure, height: int = 380, **layout) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=-0.2), **layout)
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _arrow(fig, p0, p1, color, width=2, shrink=0.075):
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    length = (dx * dx + dy * dy) ** 0.5 or 1.0
    ux, uy = dx / length, dy / length
    fig.add_annotation(x=x1 - ux * shrink, y=y1 - uy * shrink, ax=x0 + ux * shrink, ay=y0 + uy * shrink, xref="x", yref="y", axref="x", ayref="y",
                       showarrow=True, arrowhead=3, arrowsize=1.3, arrowwidth=width, arrowcolor=color, text="")


def edge_roles(a: Analysis) -> dict:
    """Rolle jeder Kante: 'causal' (auf einem kausalen Pfad), 'open' (auf einem offenen Rückweg), 'blocked' (nur auf blockierten Rückwegen), sonst 'other'."""
    role = {}
    for j, ps in enumerate(a.parents):
        for i in ps:
            role[(i, j)] = "other"

    def mark(nodes, arrows, value, only_if=None):
        for u, v, ar in zip(nodes, nodes[1:], arrows):
            e = (u, v) if ar == "→" else (v, u)
            if only_if is None or role.get(e) in only_if:
                role[e] = value

    for p in a.check.blocked_paths:
        mark(p.nodes, p.arrows, "blocked", only_if=("other",))
    for p in a.check.open_paths:
        mark(p.nodes, p.arrows, "open", only_if=("other", "blocked"))
    for path in a.causal_paths:
        for u, v in zip(path, path[1:]):
            role[(u, v)] = "causal"
    return role


def build_diagram(a: Analysis) -> go.Figure:
    """Diagramm mit Behandlung x (schwarzer Rand), Wirkung y, Menge z (blau), unbeobachteten Knoten (grau) und verbotenen Nachfahren (roter Rand)."""
    s = a.settings
    pos = C.WORLDS[s.world]["pos"]
    colors = {"causal": C.COLOR_CAUSAL, "open": C.COLOR_OPEN, "blocked": C.COLOR_BLOCKED, "other": C.COLOR_EDGE}
    fig = go.Figure()
    for (i, j), role in sorted(edge_roles(a).items()):
        _arrow(fig, pos[i], pos[j], colors[role], 3 if role in ("causal", "open") else 2)
    fills, lines, widths, texts = [], [], [], []
    for v, name in enumerate(a.names):
        hidden = v in s.hidden
        in_z = v in s.z
        forbidden = v in a.check.descendants_in_z
        fills.append(C.COLOR_HIDDEN if hidden else ("rgba(76,120,168,0.40)" if in_z else "rgba(47,107,101,0.12)"))
        lines.append(C.COLOR_FORBIDDEN if forbidden else ("#1b1b1b" if v in (s.x, s.y) else (C.COLOR_COND if in_z else C.COLOR_CAUSAL)))
        widths.append(4 if (forbidden or v in (s.x, s.y)) else 1.5)
        texts.append(name + ("<br>(unbeobachtet)" if hidden else ("<br>(Behandlung)" if v == s.x else ("<br>(Wirkung)" if v == s.y else ""))))
    fig.add_trace(go.Scatter(x=[p[0] for p in pos], y=[p[1] for p in pos], mode="markers+text", text=texts, textposition="middle center",
                             marker=dict(size=NODE_SIZE, color=fills, line=dict(width=widths, color=lines)), hoverinfo="skip", showlegend=False))
    fig.update_xaxes(visible=False, range=[-0.2, 1.2])
    fig.update_yaxes(visible=False, range=[-0.25, 1.2])
    return _fixed(fig, 380, showlegend=False)


def _path_text(names, p: G.PathInfo) -> str:
    out = names[p.nodes[0]]
    for ar, v in zip(p.arrows, p.nodes[1:]):
        out += f" {ar} {names[v]}"
    return out


def build_paths_table(a: Analysis) -> pd.DataFrame:
    rows = []
    for path in a.causal_paths:
        rows.append({"Art": "kausaler Pfad", "Pfad": " → ".join(a.names[v] for v in path), "Zustand": "trägt die Wirkung"})
    for p in a.check.open_paths:
        rows.append({"Art": "Rückweg", "Pfad": _path_text(a.names, p), "Zustand": "offen: verzerrt die Schätzung"})
    for p in a.check.blocked_paths:
        why = f"blockiert durch {a.names[p.blocker]}" if p.kind == "bedingt" else f"blockiert: Collider {a.names[p.blocker]} ist nicht vorgegeben"
        rows.append({"Art": "Rückweg", "Pfad": _path_text(a.names, p), "Zustand": why})
    return pd.DataFrame(rows if rows else [{"Art": "–", "Pfad": "keine Pfade zwischen x und y", "Zustand": "–"}])


def build_sets_table(a: Analysis) -> pd.DataFrame:
    rows = []
    for r in a.rows:
        rows.append({
            "Menge": "{" + ", ".join(a.names[v] for v in r.z) + "}" if r.z else "{} (leer)",
            "Backdoor": "gültig" if r.backdoor else "ungültig",
            "Adjustierungskriterium": "gültig" if r.adjustment else "ungültig",
            "Fehler in der Population": signed(r.bias, 2),
        })
    return pd.DataFrame(rows)


def style_sets_table(df: pd.DataFrame, current: str):
    def row_style(row):
        if row["Menge"] == current:
            return ["background-color: rgba(76,120,168,0.28)"] * len(row)
        if row["Backdoor"] == "gültig":
            return ["background-color: rgba(47,107,101,0.14)"] * len(row)
        return [""] * len(row)

    return df.style.apply(row_style, axis=1)


def build_sets_chart(rows: list) -> go.Figure:
    labels = ["{" + ", ".join(r["names"]) + "}" if r["names"] else "{}" for r in rows]
    fig = go.Figure(go.Bar(x=labels, y=[100 * r["cover"] for r in rows], marker_color=[C.COLOR_CAUSAL if r["valid"] else C.COLOR_FORBIDDEN for r in rows],
                           text=[de(100 * r["cover"], 0) for r in rows], textposition="outside"))
    fig.add_hline(y=95, line=dict(color="#888888", dash="dot"), annotation_text="versprochen: 95 %", annotation_position="top left")
    fig.update_yaxes(title="Deckung der wahren Wirkung (%)", range=[0, 115])
    fig.update_xaxes(tickangle=-45)
    return _fixed(fig, 420, showlegend=False)


def build_recipes_chart(res: dict) -> go.Figure:
    names = list(res["all"])
    fig = go.Figure()
    fig.add_trace(go.Bar(name="alle Diagramme", x=names, y=[100 * res["all"][k] / res["n_all"] for k in names], marker_color=C.COLOR_COND))
    fig.add_trace(go.Bar(name="x hat einen Elternknoten", x=names, y=[100 * res["with_parent"][k] / res["n_parent"] for k in names], marker_color=C.COLOR_OPEN))
    fig.update_yaxes(title="Menge ist gültig in … % der Diagramme", range=[0, 105])
    fig.update_layout(barmode="group")
    return _fixed(fig, 380)


def build_criterion_chart(c: dict) -> go.Figure:
    labels = ["gültig und richtig", "gültig und falsch", "ungültig und trotzdem richtig", "ungültig und falsch"]
    keys = ["valid_correct", "valid_wrong", "invalid_correct", "invalid_wrong"]
    colors = [C.COLOR_CAUSAL, C.COLOR_FORBIDDEN, C.COLOR_OPEN, C.COLOR_BLOCKED]
    fig = go.Figure(go.Bar(x=labels, y=[c[k] for k in keys], marker_color=colors, text=[f"{c[k]:,}".replace(",", ".") for k in keys], textposition="outside"))
    fig.update_yaxes(title="Anzahl Diagramm-Mengen-Paare")
    return _fixed(fig, 340, showlegend=False)


def build_hidden_chart(h: dict) -> go.Figure:
    labels = ["verborgen: Vorfahr von x", "verborgen: sonst"]
    vals = [100 * h["common"][1] / max(h["common"][0], 1), 100 * h["other"][1] / max(h["other"][0], 1)]
    fig = go.Figure(go.Bar(x=labels, y=vals, marker_color=[C.COLOR_FORBIDDEN, C.COLOR_CAUSAL], text=[de(v, 0) + " %" for v in vals], textposition="outside"))
    fig.update_yaxes(title="keine gültige beobachtete Menge (%)", range=[0, 105])
    return _fixed(fig, 340, showlegend=False)
