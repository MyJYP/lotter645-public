from pathlib import Path
from streamlit.testing.v1 import AppTest

SRC = Path(__file__).resolve().parents[1] / 'src'
DATA = SRC.parent / 'Data/645_251227.csv'
SCRIPT = f'''
import sys
sys.path.insert(0, {str(SRC)!r})
from data_loader import LottoDataLoader
from pattern_preference_ui import render_pattern_preference
loader = LottoDataLoader({str(DATA)!r})
loader.load_data()
loader.preprocess()
loader.extract_numbers()
render_pattern_preference(loader.numbers_df)
'''


def test_repeated_clicks_settings_history_and_isolation():
    app = AppTest.from_string(SCRIPT, default_timeout=30).run()
    assert not app.exception
    app.button(key='pattern_generate').click().run()
    assert not app.exception
    first = app.session_state['pattern_draw_history'][0]
    assert 'Pattern Preference Score' in app.metric[0].label
    app.slider(key='pattern_weight_pair').set_value(80).run()
    assert len(app.session_state['pattern_draw_history']) == 1
    app.button(key='pattern_generate').click().run()
    assert not app.exception
    rows = app.session_state['pattern_draw_history']
    assert len(rows) == 2 and rows[0]['numbers'] != rows[1]['numbers']
    assert rows[1]['config']['weights'][0] == 80
    other = AppTest.from_string(SCRIPT, default_timeout=30).run()
    assert other.session_state['pattern_draw_history'] == []
    app.button(key='pattern_clear').click().run()
    assert app.session_state['pattern_draw_history'] == []


def test_ui_shows_relaxation_and_invalid_settings():
    # One observed row makes most pairs unobserved, forcing the ordered fallback.
    script = SCRIPT.replace('render_pattern_preference(loader.numbers_df)', 'render_pattern_preference(loader.numbers_df.head(1))')
    app = AppTest.from_string(script, default_timeout=30).run()
    app.button(key='pattern_generate').click().run()
    assert not app.exception
    result = app.session_state['pattern_draw_history'][-1]
    assert result['stage'] == 3
    assert any('용지 그리드 조건 완화 → 구간 비율 조건 완화 → 상극 쌍 기준 완화' in item.value for item in app.warning)
    for name in ('pair', 'sequence', 'zone', 'grid'):
        app.slider(key='pattern_weight_'+name).set_value(0)
    app.button(key='pattern_generate').click().run()
    assert not app.exception
    assert len(app.session_state['pattern_draw_history']) == 1
    assert any('가중치' in item.value for item in app.error)


def test_real_app_routes_to_default_pattern_engine():
    app = AppTest.from_file(str(SRC / 'web_app.py'), default_timeout=60).run()
    assert not app.exception
    assert not app.error
    app.sidebar.radio[0].set_value('🎯 번호 추천').run()
    assert not app.exception
    assert app.radio(key='recommendation_mode').value == '패턴 선호도 1세트 연속 추출'
    app.button(key='pattern_generate').click().run()
    app.button(key='pattern_generate').click().run()
    assert not app.exception
    assert not app.error
    rows = app.session_state['pattern_draw_history']
    assert len(rows) == 2 and rows[0]['numbers'] != rows[1]['numbers']
    app.radio(key='recommendation_mode').set_value('기존 전략 (보조)').run()
    assert not app.exception
    assert len(app.session_state['pattern_draw_history']) == 2
