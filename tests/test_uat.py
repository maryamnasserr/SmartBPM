"""Regression checks for verified reset warning and research-cohort clarity."""
from datetime import date
from pathlib import Path
import logging
import pytest

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.integration
def test_reset_uses_one_widget_value_source(monkeypatch,caplog):
    from streamlit.testing.v1 import AppTest
    from streamlit.elements.lib import policies
    monkeypatch.setattr(policies,'_shown_default_value_warning',False)
    caplog.set_level(logging.WARNING,logger='streamlit.elements.lib.policies')
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=90).run()
    assert not app.exception
    initial_dates=app.sidebar.date_input[0].value
    initial_duration=app.sidebar.slider[0].value
    assert len(initial_dates)==2 and len(initial_duration)==2
    app.sidebar.date_input[0].set_value((date(2017,1,9),date(2017,1,9))).run()
    app.sidebar.slider[0].set_value((1.,20.)).run()
    app.sidebar.multiselect[0].set_value([]).run()
    assert app.metric[0].value=='0'
    app.sidebar.radio[0].set_value('ML Preparation').run()
    assert not app.exception and app.metric[0].value=='9,536'
    app.sidebar.button[0].click().run()
    app.sidebar.radio[0].set_value('Overview').run()
    assert not app.exception
    assert app.metric[0].value=='10,500'
    assert app.sidebar.date_input[0].value==initial_dates
    assert app.sidebar.slider[0].value==initial_duration
    assert len(app.sidebar.multiselect[0].value)==17
    assert len(app.sidebar.multiselect[1].value)==2
    assert not [r for r in caplog.records if 'default value' in r.getMessage() and 'Session State' in r.getMessage()]


@pytest.mark.integration
def test_research_view_distinguishes_landmark_from_final_dataset():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=90).run()
    app.sidebar.radio[0].set_value('Performance Investigation').run()
    assert not app.exception
    text=' '.join(x.value for x in [*app.markdown,*app.caption])
    assert 'Event-2 snapshots: 10,366' in text
    assert 'not the final ML-ready count' in text
    assert 'sensitivity-only' in text
