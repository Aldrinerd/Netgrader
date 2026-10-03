# tests/test_linked_report_markup.py
"""The Grading screen's linked-report hosts exist for both roles (spec 5)."""
import re

import pytest

from tests.test_frontend_modules import render_page


@pytest.mark.parametrize("instructor", [True, False])
def test_linked_report_hosts_exist(instructor):
    html = render_page(instructor)
    assert 'id="linked-report-list"' in html
    assert re.search(
        r'<section id="checkpoint-detail" class="checkpoint-detail" role="region" '
        r'aria-label="Checkpoint detail" tabindex="-1" hidden>', html)
    assert re.search(r'<div class="context-actions" id="context-actions" hidden>', html)
    for element_id in ("context-file-chips", "grade-again-btn", "clear-report-btn"):
        assert f'id="{element_id}"' in html


def test_old_scorecard_is_gone():
    html = render_page(False)
    for gone in ("report-results-list", "filter-count-all", "report-study-topics",
                 "report-grade-letter", "report-progress-fill"):
        assert f'id="{gone}"' not in html
    assert 'class="filter-chip' not in html
