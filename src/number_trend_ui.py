"""Public views of observed number trends and attributed prize amounts."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from time_series import (
    build_appearance, build_prize_allocation, prepare_trend_data,
    summarize_bonus, summarize_trend_coverage,
)

cached_appearance = st.cache_data(show_spinner=False)(build_appearance)
cached_allocation = st.cache_data(show_spinner=False)(build_prize_allocation)
cached_bonus = st.cache_data(show_spinner=False)(summarize_bonus)


def _sources():
    st.caption('과거 본번호·보너스 출현을 살펴보는 재미용 분석입니다. '
               '공정하고 독립적인 추첨에서 모든 6개 조합의 당첨 확률은 같습니다.')
    with st.expander('계산 방법'):
        st.write('번호별 출현을 1, 미출현을 0으로 기록해 최근 N회의 평균을 계산합니다. '
                 '자료가 누락된 구간은 자료 부족으로 표시합니다. '
                 '5·10·20·60·120회선에서 120회는 약 2년 4개월의 기록입니다.')
        st.write('상향 교차는 직전 5회선이 20회선 이하이고 이번에 위로 이동한 경우, '
                 '하향 교차는 그 반대입니다. 출현률과 금액 배분은 이 앱의 분석 규칙입니다.')
    st.markdown('[당첨 데이터 · 동행복권](https://www.dhlottery.co.kr/lt645/winNumber) · '
                '[이동평균 기간 · 키움증권](https://www1.kiwoom.com/wm/fnd/fs010/fndTechIndiGuidePop) · '
                '[이동평균·교차 · Fidelity](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/sma)')



COLORS = {5: '#087e82', 10: '#7e8994', 20: '#347bd2', 60: '#c58b27', 120: '#8c5bb7'}
CROSS_LABELS = {'up': '▲ 상향 교차', 'down': '▼ 하향 교차', 'none': '교차 없음'}


def _cross_label(value):
    return '자료 부족' if pd.isna(value) else CROSS_LABELS[value]


def _apply_number_selection(table_key, number_key, numbers):
    rows = st.session_state.get(table_key, {}).get('selection', {}).get('rows', [])
    if rows:
        st.session_state[number_key] = int(numbers[rows[0]])


def _render_appearance(history, kind='main'):
    prefix = f'number_trend_{kind}'
    controls = st.columns(2)
    number = controls[0].selectbox('관심 번호', list(range(1, 46)), key=f'{prefix}_number')
    period = controls[1].selectbox('표시 기간', [50, 100, 200, None], index=1,
                                  format_func=lambda n: '전체' if n is None else f'최근 {n}회',
                                  key=f'{prefix}_period')
    windows = st.multiselect('표시할 이동평균선', list(COLORS), default=[5, 20, 60, 120],
                             format_func=lambda n: f'{n}회선', key=f'{prefix}_windows')
    appearance = cached_appearance(history, kind=kind, recent_rounds=period)
    selected = appearance.loc[appearance['번호'].eq(number)]
    last = selected.iloc[-1]
    metrics = st.columns(4)
    for column, window in zip(metrics, (5, 20, 60, 120)):
        value = last[f'ma_{window}']
        count = last[f'count_{window}']
        column.metric(f'최근 {window}회 출현률', '자료 부족' if pd.isna(value) else f'{value:g}%')
        column.caption('자료 부족' if pd.isna(count) else f'{window}회 중 {int(count)}회 출현')
    figure = go.Figure()
    for window in windows:
        figure.add_trace(go.Scatter(x=selected['회차'], y=selected[f'ma_{window}'],
                                   name=f'{window}회선', mode='lines', connectgaps=False,
                                   line={'color': COLORS[window]}))
    if 5 in windows and 20 in windows:
        for cross, symbol in [('up', 'triangle-up'), ('down', 'triangle-down')]:
            points = selected.loc[selected['cross'].eq(cross).fillna(False)]
            figure.add_trace(go.Scatter(x=points['회차'], y=points['ma_5'], mode='markers',
                                       name=CROSS_LABELS[cross], marker={'symbol': symbol, 'size': 9}))
    hits = selected.loc[selected['appeared'].eq(1)]
    figure.add_trace(go.Scatter(x=hits['회차'], y=[0] * len(hits), mode='markers',
                               name='보너스 출현' if kind == 'bonus' else '본번호 출현',
                               marker={'size': 5, 'color': '#64757d'}, yaxis='y2'))
    figure.add_hline(y=100 / 45 if kind == 'bonus' else 600 / 45,
                    line_dash='dot', annotation_text='이론 기준 2.22%' if kind == 'bonus' else '이론 기준 13.33%')
    figure.update_layout(height=390, margin={'l': 15, 'r': 15, 't': 25, 'b': 25},
                         xaxis={'title': '회차', 'anchor': 'y2'},
                         yaxis={'title': '출현률 (%)', 'range': [0, 100], 'domain': [0.16, 1]},
                         yaxis2={'domain': [0, 0.07], 'visible': False, 'range': [-1, 1]},
                         legend={'orientation': 'h'}, hovermode='x unified')
    st.plotly_chart(figure, width='stretch', key=f'{prefix}_chart')
    st.caption(f"{int(last['회차'])}회 기준 · {number}번 · {_cross_label(last['cross'])}")
    latest = appearance.loc[appearance['회차'].eq(appearance['회차'].max())].copy()
    latest['cross'] = latest['cross'].map(_cross_label)
    latest = latest[['번호', 'ma_5', 'ma_20', 'ma_60', 'ma_120', 'cross']].rename(columns={
        'ma_5': '5회 출현률 (%)', 'ma_20': '20회 출현률 (%)',
        'ma_60': '60회 출현률 (%)', 'ma_120': '120회 출현률 (%)', 'cross': '이번 회차 교차'})
    st.write('전체 번호 한눈에 보기')
    table_key = f'{prefix}_table'
    st.dataframe(latest, hide_index=True, width='stretch', key=table_key,
                 on_select=lambda: _apply_number_selection(table_key, f'{prefix}_number', latest['번호'].tolist()),
                 selection_mode='single-row')
    return number, int(appearance['회차'].min()), int(appearance['회차'].max())

def render_number_trends(loader):
    st.subheader('재미로 보는 번호 차트')
    try:
        history = prepare_trend_data(loader.numbers_df, loader.df)
        coverage = summarize_trend_coverage(history)
    except (ValueError, TypeError, KeyError) as error:
        st.error(f'분석 자료를 확인해 주세요. {error}')
        _sources()
        return
    if history.empty:
        st.info('표시할 당첨 자료가 없습니다.')
        _sources()
        return
    date = coverage['last_draw_date']
    date_text = date.strftime('%Y-%m-%d') if pd.notna(date) else '날짜 미상'
    st.caption(f"보유 데이터 {coverage['start_round']}~{coverage['end_round']}회 · 마지막 추첨일 {date_text}")
    if coverage['missing_rounds'] or coverage['missing_bonus_rounds']:
        st.info(f"누락 회차 {coverage['missing_rounds']}건 · 보너스 결측 {coverage['missing_bonus_rounds']}건")
    view = st.radio('보기', ['출현 흐름', '당첨금 배분', '보너스 번호'],
             horizontal=True, key='number_trend_view')
    if view == '출현 흐름':
        _render_appearance(history)
    _sources()
