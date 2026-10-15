# Backdoor-Adjustierung: die Hintertüren schließen – Streamlit-Demo

Drittes Stück der Linie **Kausale Diagramme und Adjustierung** in der „Konzepte“-Reihe im Portfolio von [Sebastian Hanisch](https://sebastianhanisch.net) (Operations Research und Machine Learning). Nachfolger von [d-separation-demo](https://github.com/sebastian-hanisch/d-separation-demo): Dort stand, was ein Diagramm über die Daten behauptet. Hier steht, welche Variablen man festhalten muss, damit ein Koeffizient die Wirkung trifft.

## Kernfrage

Man kontrolliert nicht „alles“, sondern sperrt die Rückwege. Das **Backdoor-Kriterium** sagt aus dem Diagramm allein, welche Mengen von Variablen die Wirkung von x auf y treffen: Die Menge enthält keinen Nachfahren von x, und jeder Pfad, der mit einem Pfeil in x hineinführt, ist blockiert. Wie viele Mengen sind gültig, stimmen die Standardrezepte, ist das Kriterium auch notwendig, und was passiert, wenn eine Variable fehlt?

## Modell

- **Welten** (feste Diagramme, Knoten in topologischer Reihenfolge): das 6-Knoten-Beispiel (Region, Wetter, Schwankung, Faktor, Lieferverzug, Servicegrad; 7 Pfeile), die beiden Diagramme aus dem ersten Stück (A: Schwankung → Faktor, B: Faktor → Schwankung) und eine Mediator-Welt (Schwankung → Faktor, Faktor → Bestand → Servicegrad, Faktor → Servicegrad).
- **Daten:** lineares Normalmodell mit Einheitsrauschen aus dem Diagramm (Generator `kausal_generator.py`, wortgleich in allen Stücken der Linie).
- **Frage:** Behandlung x, Wirkung y, Adjustierungsmenge Z und unbeobachtete Knoten wählt man frei. Die **wahre Wirkung** ist die Summe der Pfadprodukte (Intervention im Modell).

## Methodik

- **Backdoor-Kriterium** (Pearl) über die Pfade mit Blockierungsgrund aus `dsep_graph.py` (wortgleich aus d-separation-demo). Der Graph ohne die von x ausgehenden Kanten ist der zweite Rechenweg im Test.
- **Adjustierungskriterium** (Shpitser, VanderWeele, Robins) als allgemeinere Zusatzzeile: Es erlaubt auch Nachfahren von x, wenn sie auf keinem kausalen Pfad liegen und keine Verzerrung öffnen.
- **Schätzer:** Koeffizient von x in der linearen Regression auf x und Z mit 95-%-Intervall (Normalnäherung). Die Adjustierungsformel steht im 📐-Expander.
- **Experimente** laufen über feste Zufallsströme (SplitMix64, ganzzahlig, plattformstabil).

## Befunde (gemessen, keine Behauptungen)

Alle Zahlen stehen in `tests/test_claims.py`.

| Frage | Befund | Test |
|---|---|---|
| Welche Mengen treffen in der 6-Knoten-Welt die Wirkung 0,50? | **8 von 16** Mengen sind gültig: genau die, die die Schwankung enthalten. Deckung des 95-%-Intervalls bei n = 500: zwischen 94 und 97 %, im Mittel 96 %. Die 8 ungültigen decken in **0 %**. | `test_experiment_1_eight_of_sixteen_sets_are_valid_all_with_the_fluctuation`, `test_experiment_1_coverage_valid_about_ninety_six_invalid_zero` |
| Wie groß ist der Fehler ungültiger Mengen? | In der Population −0,55 (leere Menge, Wetter), −0,36 (Lieferverzug), −0,30 (Region); die Schätzung liegt bei 0,2 bis −0,06 statt 0,50. Die gültigen Mengen haben den Fehler 0. | `test_experiment_1_population_errors_of_the_invalid_sets` |
| Zwei Rückwege | Faktor ← Schwankung → Servicegrad und Faktor ← Schwankung ← Region → Lieferverzug → Servicegrad; beide laufen über die Schwankung. | `test_the_two_backdoor_paths_of_the_six_node_world` |
| Standard-Stichprobe (n = 500, Seed 35) | Menge {Schwankung}: Schätzung 0,48, Intervall deckt 0,50; beide Rückwege blockiert. | `test_default_sample_in_the_six_node_world` |
| Dieselbe Menge in den Diagrammen A und B | {Schwankung} ist in A gültig, in B ungültig (Nachfahre des Faktors); die leere Menge ist in B gültig. | `test_diagrams_a_and_b_give_opposite_verdicts_for_the_same_set` |
| Alles kontrollieren | Mediator-Welt: Wirkung 0,7 (0,3 direkt + 0,5 · 0,8 über den Bestand). {Schwankung}: 0,7; {Schwankung, Bestand}: **0,3** (nur der direkte Weg). | `test_mediator_world_effect_is_0_7_and_everything_controlled_gives_0_3` |
| Welche Rezepte gelten? (600 Zufallsdiagramme mit 6 Knoten) | Gültig sind: Eltern von x und alle Nicht-Nachfahren von x in **100 %**; die leere Menge in 70 % (25 %, wenn x einen Elternknoten hat); alle Vorfahren von y in 59 % (70 %); **alle anderen Variablen nur in 14 %** (24 % mit Elternknoten von x). Je Diagramm im Mittel 4,5 gültige Mengen von 16. | `test_experiment_2_recipe_counts`, `test_experiment_2_valid_sets_per_diagram` |
| Trifft das Kriterium die Wahrheit? (400 Zufallsdiagramme, 6 400 Diagramm-Mengen-Paare, zufällige Koeffizienten, Population) | Von 2 334 gültigen Mengen treffen **alle 2 334** die Wirkung. 903 Paare (14 %) sind ungültig und trotzdem richtig; das Adjustierungskriterium stimmt mit „Koeffizient richtig“ in allen 6 400 Paaren überein. | `test_experiment_3_the_criterion_never_fails_and_is_not_necessary` |
| Wenn eine Variable fehlt (800 Diagramme mit 7 Knoten, eine zufällig verborgen) | War die verborgene Variable eine gemeinsame Ursache von x und y (115 Fälle), gibt es in **51 %** keine gültige beobachtete Menge; sonst (685 Fälle) in 0 %. | `test_experiment_4_hidden_common_cause` |

## Ehrliche Grenzen

| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| **Das Diagramm ist richtig** | Das Kriterium ist eine Aussage über das gezeichnete Diagramm. Fehlt ein Pfeil, den es in der Welt gibt, kann eine „gültige“ Menge daneben liegen. | Wie falsch darf das Diagramm sein? |
| **Alle relevanten Variablen sind beobachtet** | Bei einer verborgenen gemeinsamen Ursache gibt es in 51 % der Fälle keine gültige Menge. | Frontdoor, Instrumente |
| **Mehr Kontrolle ist besser** | „Alle anderen Variablen“ ist nur in 14 % der Diagramme gültig. | Schlechte Kontrollen |
| **Die gültige Menge ist die beste** | Gültig heißt unverzerrt, nicht genau; die Streuung der Schätzung unterscheidet sich je Menge. | Welche Menge? |
| **Es gibt Vergleichsstandorte mit und ohne hohen Faktor** | Das Kriterium sagt nichts über die Überlappung. | Schätzen |
| **Die Regression ist die richtige Form** | Die Demo schätzt linear. | Doppelt robust und Double ML |

Die Zahlen gelten für diese erfundene Welt und für zufällige Diagramme dieser Generatorfamilie (6 bis 7 Knoten, Kantenwahrscheinlichkeit 0,3 bis 0,6, Koeffizienten ±0,4 bis ±1,2); „Wahrheit“ ist das simulierte Modell, nicht ein Befund über echte Standorte.

## Bezug zu den Nachbarn im Portfolio

- [d-separation-demo](https://github.com/sebastian-hanisch/d-separation-demo): liefert die d-Separation und die Pfade; das Modul `dsep_graph.py` ist wortgleich übernommen.
- [konfundierung-demo](https://github.com/sebastian-hanisch/konfundierung-demo): zeigt, dass der naive Vergleich daneben liegt und die Schwankung als Kontrolle hilft; hier steht, warum und für welche Mengen.
- [off-policy-demo](https://github.com/sebastian-hanisch/off-policy-demo): Gewichten mit der bekannten Protokoll-Wahrscheinlichkeit; hier geht es um die Wahl der Variablen, nicht um den Schätzer.

## Tests

Mini-Instanzen von Hand (Koeffizient 1,5 gegen 2 und die Mediator-Welt mit 0,7 / 0,2 / −0,2 / 0,3), Kriterium gegen den Graphen ohne Ausgangskanten (`networkx`) auf allen Diagrammen mit 3 und 4 Knoten und 250 Zufallsdiagrammen, Population (gültig ⟹ richtig, Adjustierungskriterium genau), Gegenprobe mit Koeffizient 0, Generator (SplitMix64, Intervention gegen Pfadsumme), Auswertung, jede README-Zahl in `test_claims.py`, AppTest (Presets, Welt-Wechsel, Menge, unbeobachtete Knoten, Permalink, PDF), Footer und Laufzeit-Importe.

```bash
python -m pytest tests -q
```

## Dateistruktur

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Oberfläche |
| `kausal_generator.py` | gemeinsamer Generator der Linie (SplitMix64, Strukturmodell, Wirkung) |
| `dsep_graph.py` | d-Separation, Pfade, Aussagenmengen (wortgleich aus d-separation-demo) |
| `bdr_backdoor.py` | Rückwege, Backdoor- und Adjustierungskriterium, gültige Mengen, Rezepte |
| `bdr_evaluation.py` | Population, Regression, Analyse, Experimente, Verdikte |
| `bdr_visualization.py`, `bdr_pdf_export.py` | Figuren, Tabellen, PDF |
| `bdr_constants.py`, `bdr_presets.py` | Welten, Regler, Presets, Permalink, Zustandsbereinigung |
| `tests/` | Mini-Instanzen, Orakel, Claims, App |

## Bewusst nicht umgesetzt

- **Schlechte Kontrollen im Einzelnen** (Collider, M-Bias, Mediator als Kontrolle): hier nur als „ungültig“ markiert, eigenes Stück der Linie.
- **Beste Menge, Schätzer jenseits der Regression, Frontdoor, Instrumente:** eigene Stücke.
- **Diagramm selbst zeichnen:** Stück davor; hier sind die Welten fest.
- **Nichtlineare Modelle, Zeitreihen, Praxisdaten:** nicht gebaut; alle Zahlen sind erzeugt.

## Lokal ausführen

```bash
pip install -r requirements.txt
streamlit run app.py
```

Streamlit Cloud: Python 3.12.

Gebaut mit Streamlit, Plotly, numpy, pandas und fpdf2.

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zu den Demos: [Interaktive Demos](https://sebastianhanisch.net/demos.html).
