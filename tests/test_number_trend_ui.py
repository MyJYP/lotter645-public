from pathlib import Path
import json
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = f'''
import sys
sys.path.insert(0, {str(ROOT / 'src')!r})
from data_loader import LottoDataLoader
from number_trend_ui import render_number_trends
loader = LottoDataLoader({str(ROOT / 'Data/645_251227.csv')!r})
loader.load_data()
loader.preprocess()
loader.extract_numbers()
render_number_trends(loader)
'''


def test_trend_entry_data_range_and_view_selection():
    app = AppTest.from_string(SCRIPT, default_timeout=30).run()
    assert not app.exception and not app.error
    assert any('1249' in caption.value for caption in app.caption)
    for view in ['당첨금 배분','보너스 번호','출현 흐름']:
        app.radio(key='number_trend_view').set_value(view).run()
        assert not app.exception
    assert any('동행복권' in item.value for item in app.markdown)



def test_appearance_number_period_windows_and_table_selection():
    app = AppTest.from_string(SCRIPT, default_timeout=30).run()
    assert not app.exception
    app.selectbox(key='number_trend_main_number').set_value(35).run()
    app.selectbox(key='number_trend_main_period').set_value(50).run()
    app.multiselect(key='number_trend_main_windows').set_value([10,120]).run()
    assert not app.exception
    assert len(app.get('plotly_chart')) == 1
    assert any('35번' in caption.value for caption in app.caption)
    # Dataframe selection callbacks execute before the next widget render.
    app.session_state['number_trend_main_table']={'selection':{'rows':[6]}}
    callback_script = SCRIPT.replace('render_number_trends(loader)',
        "from number_trend_ui import _apply_number_selection\n"
        "st = __import__('streamlit')\n"
        "st.session_state['selected_table']={'selection':{'rows':[6]}}\n"
        "_apply_number_selection('selected_table','number_trend_main_number',list(range(1,46)))\n"
        "render_number_trends(loader)")
    selected = AppTest.from_string(callback_script, default_timeout=30).run()
    assert not selected.exception
    assert selected.selectbox(key='number_trend_main_number').value == 7



def test_prize_basis_period_comparison_and_empty_selection():
    app = AppTest.from_string(SCRIPT, default_timeout=30).run()
    app.radio(key='number_trend_view').set_value('당첨금 배분').run()
    assert not app.exception
    total = app.metric[0].value
    app.selectbox(key='number_trend_prize_basis').set_value('per_game').run()
    assert not app.exception and app.metric[0].value != total
    per_game_total = app.metric[0].value
    app.selectbox(key='number_trend_prize_period').set_value(60).run()
    app.selectbox(key='number_trend_prize_period').set_value(0).run()
    assert app.metric[0].value == per_game_total
    app.multiselect(key='number_trend_prize_numbers').set_value([1,38]).run()
    assert not app.exception
    assert len(app.get('plotly_chart')) == 1
    app.multiselect(key='number_trend_prize_numbers').set_value([]).run()
    assert not app.exception and not app.get('plotly_chart')
    assert any('번호를 선택' in item.value for item in app.info)



def test_appearance_displays_difference_and_line_relationship():
    app = AppTest.from_string(SCRIPT, default_timeout=30).run()
    assert not app.exception
    assert any('차이 -10%p' in item.value and '아래에 있음' in item.value for item in app.caption)
    assert '5회 − 20회 (%p)' in app.dataframe[0].value.columns
    app.selectbox(key='number_trend_main_number').set_value(2).run()
    assert not app.exception
    assert any('같음' in item.value and '차이 +0%p' in item.value for item in app.caption)



def test_bonus_view_reuses_chart_and_exposes_followup_and_money():
    app = AppTest.from_string(SCRIPT, default_timeout=30).run()
    app.radio(key='number_trend_view').set_value('보너스 번호').run()
    app.selectbox(key='number_trend_bonus_number').set_value(32).run()
    app.selectbox(key='number_trend_bonus_period').set_value(0).run()
    assert not app.exception and not app.error
    assert any(metric.label=='선택 기간 보너스 출현' and metric.value=='23회' for metric in app.metric)
    assert any('다음 회차 본번호 등장' in item.value for item in app.markdown)
    assert any('2등 총액 합계' in metric.label for metric in app.metric)
    assert len(app.get('plotly_chart'))==1


def test_real_app_routes_all_trend_views_without_errors():
    app=AppTest.from_file(str(ROOT/'src/web_app.py'),default_timeout=60).run()
    app.sidebar.radio[0].set_value('📊 데이터 탐색').run()
    assert not app.exception and not app.error
    assert any(tab.label=='재미로 보는 번호 차트' for tab in app.tabs)
    for view in ['당첨금 배분','보너스 번호','출현 흐름']:
        app.radio(key='number_trend_view').set_value(view).run()
        assert not app.exception and not app.error


import pytest


@pytest.mark.parametrize('setup,expected', [
    ("loader.numbers_df=__import__('pandas').DataFrame();loader.df=__import__('pandas').DataFrame()",'empty'),
    ("loader.numbers_df.at[0,'보너스번호']=loader.numbers_df.iloc[0]['당첨번호'][0]",'invalid'),
])
def test_empty_invalid_history_displays_feedback_and_sources(setup,expected):
    script=SCRIPT.replace('render_number_trends(loader)',setup+'\nrender_number_trends(loader)')
    app=AppTest.from_string(script,default_timeout=30).run()
    assert not app.exception
    if expected=='empty':
        assert any('표시할 당첨 자료가 없습니다' in item.value for item in app.info)
    else:
        assert any('본번호와 중복' in item.value for item in app.error)
    assert any('동행복권' in item.value for item in app.markdown)


def test_view_settings_are_isolated_between_sessions():
    first=AppTest.from_string(SCRIPT,default_timeout=30).run()
    first.selectbox(key='number_trend_main_number').set_value(35).run()
    second=AppTest.from_string(SCRIPT,default_timeout=30).run()
    assert first.selectbox(key='number_trend_main_number').value==35
    assert second.selectbox(key='number_trend_main_number').value==1



def test_prize_chart_and_table_titles_follow_basis_in_both_directions():
    app = AppTest.from_string(SCRIPT, default_timeout=30).run()
    app.radio(key='number_trend_view').set_value('당첨금 배분').run()
    for basis, label in [('total', '1등 총액 기준'), ('per_game', '1게임당 금액 기준'),
                         ('total', '1등 총액 기준')]:
        app.selectbox(key='number_trend_prize_basis').set_value(basis).run()
        assert not app.exception
        chart = json.loads(app.get('plotly_chart')[0].proto.spec)
        assert chart['layout']['title']['text'] == f'번호별 누적 배분액 · {label}'
        assert any(item.value == f'번호별 당첨금 배분 누계 · {label}' for item in app.markdown)
    app.multiselect(key='number_trend_prize_numbers').set_value([]).run()
    app.selectbox(key='number_trend_prize_basis').set_value('per_game').run()
    assert not app.exception
    assert any(item.value == '번호별 당첨금 배분 누계 · 1게임당 금액 기준' for item in app.markdown)
