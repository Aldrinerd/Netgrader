# tests/test_shell.py
"""The rail, context bar and Display menu, for the instructor and for a lab PC."""
import re

from tests.test_frontend_modules import render_page


def test_rail_is_the_main_navigation():
    html = render_page(instructor=True)
    assert re.search(r'<nav class="rail" aria-label="Main">', html)
    assert 'class="navbar"' not in html
    items = re.findall(r'data-mode="(\w+)"', html)
    assert items == ["visualizer", "teacher", "student"]


def test_lab_pc_rail_has_no_instructor_item():
    html = render_page(instructor=False)
    assert re.findall(r'data-mode="(\w+)"', html) == ["visualizer", "student"]


def test_rail_items_have_visible_labels():
    html = render_page(instructor=True)
    for label in ("Discovery", "Instructor", "Grading", "Display"):
        assert re.search(rf'<span class="rail-label">{label}</span>', html), label


def test_context_bar_names_the_screen():
    html = render_page(instructor=True)
    assert re.search(r'<h1 class="context-title" id="context-title">Topology Discovery</h1>', html)


def test_display_menu_offers_every_setting():
    html = render_page(instructor=False)
    assert re.search(r'id="display-menu"[^>]*role="dialog"[^>]*hidden', html)
    expected = {
        "textSize": ["sm", "md", "lg", "xl"],
        "theme": ["dark", "light", "system"],
        "contrast": ["standard", "high"],
        "motion": ["system", "reduce"],
    }
    for name, values in expected.items():
        assert re.findall(rf'name="{name}" value="(\w+)"', html) == values, name
    assert "easier to read on projectors" in html


def test_display_button_controls_the_menu():
    html = render_page(instructor=True)
    assert re.search(r'id="display-menu-btn"[^>]*aria-controls="display-menu"[^>]*aria-expanded="false"', html)


def test_reset_view_lives_in_the_map_toolbar():
    html = render_page(instructor=True)
    toolbar_start = html.index('class="canvas-actions"')
    canvas_start = html.index('id="canvas-viewport"')
    assert toolbar_start < html.index('id="reset-btn"') < canvas_start
