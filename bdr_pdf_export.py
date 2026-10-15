"""PDF-Export der aktuellen Prüfung (fpdf2). Kernschriften sind latin-1: Umlaute gehen, Pfeile und Sonderzeichen werden ersetzt."""

from __future__ import annotations

from fpdf import FPDF

from bdr_evaluation import Analysis, de

_REPLACE = {"→": "->", "←": "<-", "–": "-", "—": "-", "−": "-", "€": "EUR", "≥": ">=", "≤": "<=", "⊥": "_|_"}
MAX_ROWS = 40


def _s(text) -> str:
    out = str(text)
    for old, new in _REPLACE.items():
        out = out.replace(old, new)
    return out.encode("latin-1", "replace").decode("latin-1")


def build_pdf(a: Analysis) -> bytes:
    s, names = a.settings, a.names
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 9, _s("Backdoor-Adjustierung: die Hintertüren schließen"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    given = ", ".join(names[v] for v in s.z) or "keine Variable"
    hidden = ", ".join(names[v] for v in s.hidden) or "keine"
    pdf.multi_cell(0, 5, _s(f"Welt: {s.world}. Behandlung {names[s.x]}, Wirkung {names[s.y]}. Menge: {given}. Unbeobachtet: {hidden}. n = {s.n}, Seed {s.seed}. "
                            "Alles simuliert."), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    lines = [
        f"Backdoor-Kriterium: {'gültig' if a.check.valid else 'ungültig'}; offene Rückwege {len(a.check.open_paths)}, blockierte {len(a.check.blocked_paths)}.",
        f"Adjustierungskriterium: {'gültig' if a.adjustment else 'ungültig'}.",
        f"Schätzung: {de(a.estimate, 3)} (95-%-Intervall {de(a.lo, 3)} bis {de(a.hi, 3)}); wahre Wirkung {de(a.truth, 3)}; Intervall deckt: {'ja' if a.covers else 'nein'}.",
        f"Gültige Mengen unter den beobachteten Variablen: {a.n_valid} von {len(a.rows)}.",
    ]
    for line in lines:
        pdf.multi_cell(0, 5, _s(line), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 9)
    for h, w in zip(["Menge", "Backdoor", "Adjustierung", "Fehler (Pop.)"], [90, 25, 30, 30]):
        pdf.cell(w, 6, _s(h), border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 8)
    for r in a.rows[:MAX_ROWS]:
        vals = ["{" + ", ".join(names[v] for v in r.z) + "}", "ja" if r.backdoor else "nein", "ja" if r.adjustment else "nein", de(r.bias, 3)]
        for v, w in zip(vals, [90, 25, 30, 30]):
            pdf.cell(w, 5.5, _s(v)[:58], border=1)
        pdf.ln()
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(0, 4, _s("Backdoor: kein Nachfahre von x in der Menge, jeder Rückweg blockiert. Quelle: backdoor-demo, Sebastian Hanisch."), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
