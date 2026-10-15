"""End-to-end Smoke-Test via Streamlits offiziellem AppTest-Framework: lädt app.py mit den Standardeinstellungen, klickt jeden Preset-Button, fährt den Regler an
seine Grenzen, wechselt Welt, Behandlung, Wirkung, Menge und unbeobachtete Knoten und prüft, dass kein Python-Fehler auftritt."""

import os

from streamlit.testing.v1 import AppTest

import bdr_constants as C

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
TIMEOUT = 240


def _fresh_app() -> AppTest:
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    return at


def test_app_loads_without_exception_and_shows_the_default_verdict():
    at = _fresh_app()
    assert at.selectbox(key="world_select").value == C.DEFAULT_WORLD
    labels = {m.label: m.value for m in at.metric}
    assert labels["Backdoor-Kriterium"] == "gültig" and labels["Gültige Mengen"] == "8 von 16"


def test_every_button_click_does_not_raise():
    labels = [b.label for b in _fresh_app().button]
    assert labels, "keine Buttons gefunden"
    for index, label in enumerate(labels):
        at = _fresh_app()
        at.button[index].click().run(timeout=TIMEOUT)
        assert not at.exception, (label, [str(e) for e in at.exception])


def test_the_slider_at_its_min_and_max_does_not_raise():
    for edge in ("min", "max"):
        at = _fresh_app()
        s = at.slider(key="n_slider")
        s.set_value(int(s.min if edge == "min" else s.max)).run(timeout=TIMEOUT)
        assert not at.exception, (edge, [str(e) for e in at.exception])


def test_every_preset_is_applied_to_the_widgets():
    labels = {b.label: i for i, b in enumerate(_fresh_app().button)}
    for name, preset in C.PRESETS.items():
        at = _fresh_app()
        at.button[labels[name]].click().run(timeout=TIMEOUT)
        assert not at.exception, (name, [str(e) for e in at.exception])
        assert at.selectbox(key="world_select").value == preset["world"]
        assert at.selectbox(key="x_select").value == preset["x"] and at.selectbox(key="y_select").value == preset["y"]
        assert at.multiselect(key="z_select").value == list(preset["z"])
        assert at.multiselect(key="hidden_select").value == list(preset["hidden"])


def test_changing_the_world_resets_the_question():
    at = _fresh_app()
    at.selectbox(key="world_select").select("Mediator-Welt").run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    assert (at.selectbox(key="x_select").value, at.selectbox(key="y_select").value) == (1, 3)
    assert at.multiselect(key="z_select").value == [0, 2]
    assert {m.label: m.value for m in at.metric}["Backdoor-Kriterium"] == "ungültig"


def test_the_empty_set_is_invalid_and_the_confounder_valid():
    at = _fresh_app()
    at.multiselect(key="z_select").set_value([]).run(timeout=TIMEOUT)
    assert {m.label: m.value for m in at.metric}["Backdoor-Kriterium"] == "ungültig"
    at.multiselect(key="z_select").set_value([2]).run(timeout=TIMEOUT)
    assert {m.label: m.value for m in at.metric}["Backdoor-Kriterium"] == "gültig"
    assert not at.exception, [str(e) for e in at.exception]


def test_hiding_the_confounder_removes_it_from_the_set_and_shows_the_warning():
    at = _fresh_app()
    at.multiselect(key="hidden_select").set_value([2]).run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    assert 2 not in at.multiselect(key="z_select").value
    assert any("keine gültige Menge" in w.value for w in at.warning)


def test_choosing_y_equal_to_x_is_repaired():
    at = _fresh_app()
    at.selectbox(key="x_select").set_value(at.selectbox(key="y_select").value).run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    assert at.selectbox(key="x_select").value != at.selectbox(key="y_select").value


def test_world_with_fewer_nodes_after_a_selection_in_a_larger_one_does_not_raise():
    at = _fresh_app()
    at.multiselect(key="hidden_select").set_value([0, 1]).run(timeout=TIMEOUT)
    at.selectbox(key="world_select").select("Diagramm A (Schwankung → Faktor)").run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    assert all(v < 3 for v in at.multiselect(key="hidden_select").value + at.multiselect(key="z_select").value)


def test_the_truth_toggle_adds_the_metrics():
    at = _fresh_app()
    before = len(at.metric)
    at.toggle(key="reveal_truth").set_value(True).run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    assert len(at.metric) == before + 3 and any(m.label == "Wahre Wirkung (x festgesetzt)" for m in at.metric)


def test_pdf_is_created_only_after_the_click():
    at = _fresh_app()
    assert "pdf_made" not in at.session_state
    at.button(key="pdf_make").click().run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    settings, data = at.session_state["pdf_made"]
    assert data[:5] == b"%PDF-" and len(data) > 1000


def test_permalink_values_are_taken_and_invalid_ones_cleaned():
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
    at.query_params["w"] = "Mediator-Welt"
    at.query_params["x"] = "1"
    at.query_params["y"] = "1"
    at.query_params["z"] = "0,9,2"
    at.query_params["h"] = "2,7"
    at.query_params["n"] = "999999"
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    assert at.selectbox(key="world_select").value == "Mediator-Welt"
    assert at.selectbox(key="x_select").value == 1 and at.selectbox(key="y_select").value != 1
    assert at.multiselect(key="hidden_select").value == [2]
    assert at.multiselect(key="z_select").value == [0]
    assert at.slider(key="n_slider").value == C.N_MAX


def test_unknown_world_in_the_permalink_is_ignored():
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
    at.query_params["w"] = "Nirgendwo"
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    assert at.selectbox(key="world_select").value == C.DEFAULT_WORLD


def test_the_address_bar_mirrors_the_settings():
    at = _fresh_app()
    at.multiselect(key="z_select").set_value([0, 2]).run(timeout=TIMEOUT)
    assert at.query_params["z"] in ("0,2", ["0,2"])
