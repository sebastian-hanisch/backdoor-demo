"""Backdoor-Adjustierung: die Hintertüren schließen - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Drittes Stück der Linie Kausale Diagramme und Adjustierung. Ein festes Ursachen-Diagramm liefert die Daten; das Backdoor-Kriterium sagt, welche Mengen von
Variablen die Wirkung des Faktors treffen. Kern: bdr_backdoor.py und dsep_graph.py (wortgleich aus d-separation-demo), Generator: kausal_generator.py.

Lauffähig mit: streamlit run app.py
"""

import streamlit as st

import bdr_constants as C
from bdr_evaluation import (
    Settings,
    analyse,
    criterion_experiment,
    de,
    hidden_experiment,
    recipes_experiment,
    sets_experiment,
    signed,
    verdict_criterion,
    verdict_hidden,
    verdict_instance,
    verdict_no_valid_set,
    verdict_recipes,
    verdict_sets,
)
from bdr_pdf_export import build_pdf
from bdr_presets import (
    apply_preset,
    bounds,
    clean_state,
    init_session_state_defaults,
    load_permalink_settings,
    n_nodes,
    on_world_change,
    randomize_seed,
    sync_query_params,
)
from bdr_visualization import (
    build_criterion_chart,
    build_diagram,
    build_hidden_chart,
    build_paths_table,
    build_recipes_chart,
    build_sets_chart,
    build_sets_table,
    style_sets_table,
)

st.set_page_config(page_title="Backdoor-Adjustierung – Sebastian Hanisch", layout="wide")

SPINNER = "Experiment rechnet über feste Zufallsströme …"


@st.cache_data(show_spinner=False)
def _analysis(settings):
    return analyse(settings)


@st.cache_data(show_spinner=SPINNER)
def _sets():
    return sets_experiment()


@st.cache_data(show_spinner=SPINNER)
def _recipes():
    return recipes_experiment()


@st.cache_data(show_spinner=SPINNER)
def _criterion():
    return criterion_experiment()


@st.cache_data(show_spinner=SPINNER)
def _hidden():
    return hidden_experiment()


def verdict(kind_text):
    kind, text = kind_text
    getattr(st, kind)(text)


st.title("🚪 Backdoor-Adjustierung: die Hintertüren schließen")
st.markdown(
    """
**Man kontrolliert nicht alles, sondern sperrt die Rückwege.** Dies ist das dritte Stück der Linie **Kausale Diagramme und Adjustierung**. Das erste Stück hat gezeigt,
dass der naive Vergleich daneben liegt, das zweite, wie man aus einem Diagramm seine Aussagen liest. Hier steht die Handlungsanweisung: Welche Variablen muss man
festhalten, damit der Koeffizient des Faktors die Wirkung trifft? Das **Backdoor-Kriterium** beantwortet es aus dem Diagramm allein: Die Menge darf keinen Nachfahren
des Faktors enthalten und muss jeden Pfad blockieren, der mit einem Pfeil **in** den Faktor hineinführt.

Weiter unten: vier Experimente (**🔬**), **🚧 Wo die Annahmen enden** und der Expander **📐 Mathematische Formulierung**.
"""
)

with st.expander("So funktioniert die Hintertür", expanded=True):
    st.markdown(
        """
1. **Kausale Pfade.** Pfeile von der Behandlung x zur Wirkung y tragen die Wirkung. Sie dürfen nicht blockiert werden.
2. **Rückwege.** Ein Pfad, der mit einem Pfeil in x hineinführt, ist ein *Rückweg*. Auf ihm laufen Einflüsse, die x und y zugleich bewegen, ohne dass x etwas bewirkt.
3. **Das Kriterium.** Eine Menge Z ist gültig, wenn sie (a) keinen Nachfahren von x enthält und (b) jeden Rückweg blockiert (Kette und Gabel durch einen Knoten in Z,
   ein Collider nur, wenn er und seine Nachfahren nicht in Z liegen).
4. **Dann gilt die Adjustierungsformel.** $P(y \\mid do(x)) = \\sum_z P(y \\mid x, z)\\,P(z)$; im linearen Modell ist das der Koeffizient von x in der Regression auf x und Z.
        """
    )

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
cols = st.columns(len(C.PRESETS))
for col, name in zip(cols, C.PRESETS):
    with col:
        st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP.get(name, ""), key=f"preset_{name}")

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()
clean_state()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    st.markdown("**Welt (liefert Diagramm und Daten)**")
    world = st.selectbox("Diagramm", C.WORLD_ORDER, key="world_select", on_change=on_world_change,
                         help="Das wahre Ursachen-Diagramm. Beim Wechsel setzt die Demo Behandlung, Wirkung, Menge und unbeobachtete Knoten auf die Voreinstellung der Welt.")
    nn = n_nodes(world)
    names = C.WORLDS[world]["nodes"]
    st.markdown("**Frage**")
    x = st.selectbox("Behandlung x", list(range(nn)), key="x_select", format_func=lambda v: names[v], help="Die Variable, deren Wirkung man wissen will.")
    y = st.selectbox("Wirkung y", [v for v in range(nn) if v != x], key="y_select", format_func=lambda v: names[v], help="Die Variable, auf die x wirkt.")
    hidden = st.multiselect("Nicht beobachtet", [v for v in range(nn) if v not in (x, y)], key="hidden_select", format_func=lambda v: names[v],
                            help="Diese Knoten lassen sich nicht in die Menge aufnehmen. Läuft ein Rückweg nur über sie, gibt es keine gültige Menge.")
    st.markdown("**Adjustierungsmenge**")
    z = st.multiselect("Festgehaltene Variablen Z", [v for v in range(nn) if v not in (x, y) and v not in hidden], key="z_select", format_func=lambda v: names[v],
                       help="Die Variablen, die man in die Regression aufnimmt.")
    st.markdown("**Daten**")
    n = st.slider("Beobachtungen n", *bounds("n_slider"), step=C.N_STEP, key="n_slider", help="Stichprobengröße der simulierten Daten.")
    seed = st.number_input("Zufalls-Seed der Stichprobe", *bounds("seed_input"), key="seed_input", step=1)
    st.button("🎲 Neue Stichprobe würfeln", width="stretch", on_click=randomize_seed)

sync_query_params({"w": world, "x": x, "y": y, "z": ",".join(str(v) for v in z), "h": ",".join(str(v) for v in hidden), "n": int(n), "seed": int(seed)})

settings = Settings(world, int(x), int(y), tuple(sorted(z)), tuple(sorted(hidden)), int(n), int(seed))
a = _analysis(settings)

# --- Ergebnis ------------------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Ergebnis")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Backdoor-Kriterium", "gültig" if a.check.valid else "ungültig",
          delta=f"{len(a.check.open_paths)} Rückweg(e) offen" if a.check.open_paths else ("verbotene Nachfahren" if a.check.descendants_in_z else "alle Rückwege blockiert"),
          delta_color="off", help="Gültig heißt: keine Nachfahren von x in der Menge und jeder Rückweg blockiert.")
c2.metric("Adjustierungskriterium", "gültig" if a.adjustment else "ungültig", delta="allgemeiner als Backdoor", delta_color="off",
          help="Das allgemeinere Kriterium erlaubt auch Nachfahren von x, die auf keinem kausalen Pfad liegen und keine Verzerrung öffnen.")
c3.metric("Schätzung (Koeffizient von x)", signed(a.estimate, 3), delta=f"95-%-Intervall {de(a.lo, 2)} bis {de(a.hi, 2)}", delta_color="off")
c4.metric("Gültige Mengen", f"{a.n_valid} von {len(a.rows)}", delta="unter den beobachteten Variablen", delta_color="off")

left, right = st.columns([1.1, 1])
with left:
    st.plotly_chart(build_diagram(a), width="stretch", key="diagram_chart")
    st.caption("Grün: kausale Pfade. Orange: offene Rückwege. Grau: blockierte Rückwege. Blau: festgehaltene Variablen. Roter Rand: Nachfahre von x in der Menge. "
               "Grauer Knoten: nicht beobachtet.")
with right:
    st.markdown("**Pfade zwischen Behandlung und Wirkung**")
    st.dataframe(build_paths_table(a), hide_index=True, width="stretch", height=min(60 + 35 * max(1, len(a.causal_paths) + len(a.check.open_paths) + len(a.check.blocked_paths)), 380))
verdict(verdict_instance(a))
nv = verdict_no_valid_set(a)
if nv:
    verdict(nv)

if st.button("📄 PDF der aktuellen Prüfung erstellen", key="pdf_make"):
    st.session_state["pdf_made"] = (settings, build_pdf(a))
made = st.session_state.get("pdf_made")
if made and made[0] == settings:
    st.download_button("⬇️ PDF herunterladen", data=made[1], file_name="backdoor-adjustierung.pdf", mime="application/pdf", key="pdf_download")

# --- Kernfrage -----------------------------------------------------------------------------------------------------------------------------

st.markdown("## ❓ Kernfrage: Trifft der Koeffizient die Wirkung?")
st.toggle("🙈 Wahrheit enthüllen (wahre Wirkung und Fehler dieser Schätzung)", key="reveal_truth")
if st.session_state.get("reveal_truth", False):
    r1, r2, r3 = st.columns(3)
    r1.metric("Wahre Wirkung (x festgesetzt)", signed(a.truth, 3))
    r2.metric("Fehler dieser Stichprobe", signed(a.estimate - a.truth, 3))
    r3.metric("Fehler im Grenzfall (n → ∞)", signed(a.pop_coef - a.truth, 3), help="Der Koeffizient der Population minus die wahre Wirkung: der Fehler, der mit mehr Daten bleibt.")
    if a.covers:
        st.success(f"Das Intervall ({de(a.lo, 2)} bis {de(a.hi, 2)}) deckt die wahre Wirkung {de(a.truth, 2)}.")
    else:
        st.warning(f"Das Intervall ({de(a.lo, 2)} bis {de(a.hi, 2)}) verfehlt die wahre Wirkung {de(a.truth, 2)}.")
st.markdown("**Alle Mengen unter den beobachteten Variablen**")
cur = "{" + ", ".join(names[v] for v in settings.z) + "}" if settings.z else "{} (leer)"
st.dataframe(style_sets_table(build_sets_table(a), cur), hide_index=True, width="stretch", height=min(60 + 35 * len(a.rows), 600))
st.caption("Blau: die aktuelle Menge. Grün hinterlegt: nach dem Backdoor-Kriterium gültig. „Fehler in der Population“ ist der Koeffizient dieser Menge minus die "
           "wahre Wirkung bei unendlich vielen Beobachtungen.")

st.markdown("---")

# --- Experimente ---------------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Experiment 1: Alle 16 Mengen der 6-Knoten-Welt")
rows1 = _sets()
st.caption(f"Faktor → Servicegrad (wahre Wirkung 0,50), alle Teilmengen von Region, Wetter, Schwankung und Lieferverzug, n = {C.EXP_SETS_N}, {C.EXP_SETS_REPS} feste "
           "Wiederholungen. Gezeigt ist, wie oft das 95-%-Intervall die wahre Wirkung enthält.")
st.plotly_chart(build_sets_chart(rows1), width="stretch", key="sets_chart")
verdict(verdict_sets(rows1))
st.dataframe(
    [{"Menge": "{" + ", ".join(r["names"]) + "}" if r["names"] else "{} (leer)", "Backdoor": "gültig" if r["valid"] else "ungültig",
      "Fehler in der Population": signed(r["bias"], 2), "Mittel der Schätzung": de(r["mean"], 2), "Deckung": f"{de(100 * r['cover'], 0)} %"} for r in rows1],
    hide_index=True, width="stretch")

st.subheader("🔬 Experiment 2: Welche Rezepte stimmen?")
res2 = _recipes()
st.caption(f"{res2['n_all']} zufällige Diagramme mit {C.RANDOM_NODES} Knoten, ein kausaler Pfad von x nach y. Gezeigt ist, in wie vielen Diagrammen das Rezept eine "
           "gültige Menge liefert.")
st.plotly_chart(build_recipes_chart(res2), width="stretch", key="recipes_chart")
verdict(verdict_recipes(res2))
mean_valid = sum(res2["valid_counts"]) / len(res2["valid_counts"])
st.caption(f"Je Diagramm gibt es im Mittel {de(mean_valid, 1)} gültige Mengen unter {2 ** (C.RANDOM_NODES - 2)} möglichen; die kleinste hat im Mittel "
           f"{de(sum(res2['min_sizes']) / len(res2['min_sizes']), 2)} Variablen.")

st.subheader("🔬 Experiment 3: Das Kriterium gegen die Wahrheit")
res3 = _criterion()
st.caption(f"{res3['diagrams']} zufällige Diagramme mit {C.RANDOM_NODES} Knoten, zufällige Koeffizienten, alle Mengen ({res3['pairs']} Paare). „Richtig“ heißt: der "
           "Regressionskoeffizient der Population ist die Gesamtwirkung.")
st.plotly_chart(build_criterion_chart(res3), width="stretch", key="criterion_chart")
verdict(verdict_criterion(res3))

st.subheader("🔬 Experiment 4: Wenn eine Variable fehlt")
res4 = _hidden()
st.caption(f"{C.EXP_HIDDEN_DIAGRAMS} zufällige Diagramme mit {C.RANDOM_NODES_HIDDEN} Knoten, eine zufällig gewählte Variable (nicht x, y) ist unbeobachtet. Gezählt wird, "
           "wie oft unter den übrigen keine gültige Menge existiert.")
st.plotly_chart(build_hidden_chart(res4), width="stretch", key="hidden_chart")
verdict(verdict_hidden(res4))

st.markdown("---")

# --- Grenzen -------------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
allr = res2["all"]["alle anderen Variablen"] / res2["n_all"]
st.markdown(
    f"""
| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| **Das Diagramm ist richtig** | Das Kriterium ist eine Aussage über das gezeichnete Diagramm. Fehlt ein Pfeil, den es in der Welt gibt, kann eine „gültige“ Menge daneben liegen. | Wie falsch darf das Diagramm sein? |
| **Alle relevanten Variablen sind beobachtet** | Bei einer verborgenen gemeinsamen Ursache gibt es in {de(100 * res4['common'][1] / max(res4['common'][0], 1), 0)} % der Fälle keine gültige Menge (Experiment 4). | Frontdoor, Instrumente |
| **Mehr Kontrolle ist besser** | „Alle anderen Variablen“ ist nur in {de(100 * allr, 0)} % der Diagramme gültig (Experiment 2); Nachfahren und Collider machen es ungültig. | Schlechte Kontrollen |
| **Die gültige Menge ist die beste** | Gültig heißt unverzerrt, nicht genau: Mengen unterscheiden sich in der Streuung der Schätzung. | Welche Menge? |
| **Es gibt Vergleichsstandorte mit und ohne hohen Faktor** | Das Kriterium sagt nichts über die Überlappung; bei fast deterministischer Auswahl fehlen Vergleiche. | Schätzen |
| **Die Regression ist die richtige Form** | Die Demo schätzt linear. Nichtlineare Abhängigkeiten verlangen andere Schätzer. | Doppelt robust und Double ML |
"""
)

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Modell.** Ein gerichteter azyklischer Graph $G$; linear mit Einheitsrauschen, $V = BV + \varepsilon$, also $\Sigma = (I-B)^{-1}(I-B)^{-\top}$ und die
Gesamtwirkungen $T = (I-B)^{-1} - I$. Die **wahre Wirkung** von $x$ auf $y$ ist $T_{yx}$, die Summe der Pfadprodukte.

**Rückweg.** Ein Pfad zwischen $x$ und $y$, dessen erste Kante in $x$ hineinführt ($x \leftarrow \dots$).

**Backdoor-Kriterium (Pearl).** $Z \subseteq V\setminus\{x,y\}$ ist eine zulässige Menge für $(x,y)$, wenn (a) kein Knoten von $Z$ ein Nachfahre von $x$ ist und (b) $Z$
jeden Rückweg blockiert. Dann ist $P(y \mid do(x)) = \sum_z P(y \mid x, z)\,P(z)$; im linearen Modell ist der Koeffizient von $x$ in $y \sim x + Z$ gleich $T_{yx}$.

**Äquivalente Formulierung.** (b) gilt genau dann, wenn $x \perp_d y \mid Z$ im Graphen $G_{\underline{x}}$ ohne die von $x$ ausgehenden Kanten; die Demo rechnet über die
Pfade mit Blockierungsgrund und prüft die zweite Fassung im Test.

**Adjustierungskriterium (Shpitser, VanderWeele, Robins).** Mit $\mathrm{forb}(x,y)$ = Knoten auf kausalen Pfaden $x \to \dots \to y$ (ohne $x$) und ihre Nachfahren: $Z$ ist
zulässig, wenn $Z \cap \mathrm{forb}(x,y) = \emptyset$ und $x \perp_d y \mid Z$ im Graphen, in dem die ersten Kanten der kausalen Pfade entfernt sind. Es ist allgemeiner
als das Backdoor-Kriterium.

**Eltern von x** und **alle Nicht-Nachfahren von x** sind immer zulässig, solange sie beobachtet sind.

**Literatur.** J. Pearl, *Causal diagrams for empirical research*, Biometrika 82, 1995; I. Shpitser, T. VanderWeele, J. Robins, *On the validity of covariate adjustment
for estimating causal effects*, UAI 2010 (beide aus dem Gedächtnis, nicht geprüft).
        """
    )

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zu den Demos: [Interaktive Demos](https://sebastianhanisch.net/demos.html)."
)
