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
    period = controls[1].selectbox('표시 기간', [50, 100, 200, 0], index=1,
                                  format_func=lambda n: '전체' if n == 0 else f'최근 {n}회',
                                  key=f'{prefix}_period')
    windows = st.multiselect('표시할 이동평균선', list(COLORS), default=[5, 20, 60, 120],
                             format_func=lambda n: f'{n}회선', key=f'{prefix}_windows')
    appearance = cached_appearance(history, kind=kind, recent_rounds=period or None)
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
    difference = last['ma_5'] - last['ma_20']
    if pd.isna(difference):
        state = '5회·20회선 자료 부족'
    else:
        relation = '같음' if difference == 0 else ('위에 있음' if difference > 0 else '아래에 있음')
        state = f'5회선이 20회선과 {relation}' if difference == 0 else f'5회선이 20회선 {relation}'
        state += f' · 차이 {difference:+g}%p'
    st.caption(f"{int(last['회차'])}회 기준 · {number}번 · {state} · {_cross_label(last['cross'])}")
    latest = appearance.loc[appearance['회차'].eq(appearance['회차'].max())].copy()
    latest['cross'] = latest['cross'].map(_cross_label)
    latest['difference'] = latest['ma_5'] - latest['ma_20']
    latest = latest[['번호', 'ma_5', 'ma_20', 'ma_60', 'ma_120', 'difference', 'cross']].rename(columns={
        'ma_5': '5회 출현률 (%)', 'ma_20': '20회 출현률 (%)',
        'ma_60': '60회 출현률 (%)', 'ma_120': '120회 출현률 (%)',
        'difference': '5회 − 20회 (%p)', 'cross': '이번 회차 교차'})
    st.write('전체 번호 한눈에 보기')
    table_key = f'{prefix}_table'
    st.dataframe(latest, hide_index=True, width='stretch', key=table_key,
                 on_select=lambda: _apply_number_selection(table_key, f'{prefix}_number', latest['번호'].tolist()),
                 selection_mode='single-row')
    return number, int(appearance['회차'].min()), int(appearance['회차'].max())


def _won_to_eok(value):
    return None if pd.isna(value) else float(value) / 100000000


def _render_prizes(history):
    controls = st.columns(2)
    basis = controls[0].selectbox('금액 기준', ['total', 'per_game'],
                                 format_func=lambda value: '1등 총액 기준' if value == 'total' else '1게임당 금액 기준',
                                 key='number_trend_prize_basis')
    period = controls[1].selectbox('집계 기간', [0, 120, 60],
                                  format_func=lambda n: '전체' if n == 0 else f'최근 {n}회',
                                  key='number_trend_prize_period')
    numbers = st.multiselect('비교할 번호', list(range(1, 46)), default=[1], max_selections=6,
                             key='number_trend_prize_numbers')
    end = int(history['회차'].max())
    start = int(history['회차'].min()) if period == 0 else max(int(history['회차'].min()), end - period + 1)
    result = cached_allocation(history, start=start, end=end, basis=basis)
    coverage = result['coverage']
    st.caption(f'{start}~{end}회 · 공시 당첨금 기준·세전 · 금액 표시는 반올림합니다.')
    st.write('각 회차의 기준 금액을 본번호 6개에 똑같이 나눠 누적한 분석용 금액입니다.')
    metrics = st.columns(4)
    metrics[0].metric('집계한 금액 합계 (억 원)', f"{coverage['total_amount'] / 100000000:,.2f}")
    for column, label, field in zip(metrics[1:], ['유효 금액 회차', '금액 제외 회차', '미관측 회차'],
                                     ['valid_prize_rounds', 'excluded_prize_rounds', 'missing_rounds']):
        column.metric(label, coverage[field])
    if not coverage['valid_prize_rounds']:
        st.warning('선택 기간에 집계 가능한 금액이 없습니다. 회차 상세의 제외 사유를 확인해 주세요.')
    elif coverage['excluded_prize_rounds'] or coverage['missing_rounds']:
        st.info('누계는 관측한 유효 금액의 합계입니다. 제외·미관측 회차는 상세에서 확인할 수 있습니다.')
    figure = go.Figure()
    for number in numbers:
        series = result['series'].loc[result['series']['번호'].eq(number)]
        values = [None if pd.isna(amount) else int(total) / 600000000
                  for amount, total in zip(series['allocation_numerator'], series['cumulative_numerator'])]
        figure.add_trace(go.Scatter(x=series['회차'], y=values, mode='lines',
                                   name=f'{number}번', connectgaps=False))
    if numbers:
        figure.update_layout(height=360, xaxis_title='회차', yaxis_title='누적 배분액 (억 원)',
                             hovermode='x unified', legend={'orientation': 'h'})
        st.plotly_chart(figure, width='stretch', key='number_trend_prize_chart')
    else:
        st.info('누적선을 비교할 번호를 선택해 주세요.')
    summary = result['summary'].sort_values('cumulative_numerator', ascending=False, kind='stable').copy()
    summary['배분 누계 (억 원)'] = summary['cumulative_numerator'].map(lambda amount: int(amount) / 600000000)
    summary['출현 회당 평균 (억 원)'] = summary['average_allocation'].map(_won_to_eok)
    display = summary[['번호', '배분 누계 (억 원)', 'appearance_count',
                       'valid_appearance_count', '출현 회당 평균 (억 원)']].rename(columns={
        'appearance_count': '본번호 출현 횟수', 'valid_appearance_count': '금액 유효 출현 횟수'})
    st.write('번호별 당첨금 배분 누계')
    st.dataframe(display, hide_index=True, width='stretch', key='number_trend_prize_table')
    with st.expander('회차별 금액·제외 사유'):
        details = result['rounds'].copy()
        details['균등 배분액 (억 원)'] = details['amount'].map(
            lambda value: None if pd.isna(value) else int(value) / 600000000)
        details = details.rename(columns={'per_game': '게임당 금액 (원)', 'winning_games': '당첨게임 수',
                                          'amount': '사용 금액 (원)', 'exclusion_reason': '제외 사유',
                                          'amount_source': '산출 근거'})
        st.dataframe(details, hide_index=True, width='stretch')


def _render_bonus(history):
    st.write('아차! 보너스 번호 탐구')
    st.caption('2등은 본번호 5개와 보너스 번호를 맞힌 경우입니다.')
    number, start, end = _render_appearance(history, kind='bonus')
    result = cached_bonus(history, start=start, end=end)
    row = result['summary'].set_index('번호').loc[number]
    metrics = st.columns(3)
    metrics[0].metric('선택 기간 보너스 출현', f"{row['bonus_count']}회")
    metrics[1].metric('마지막 보너스 출현', '기록 없음' if pd.isna(row['last_bonus_round']) else f"{row['last_bonus_round']}회")
    metrics[2].metric('경과 회차', '기록 없음' if pd.isna(row['rounds_since_bonus']) else f"{row['rounds_since_bonus']}회")
    interval = '자료 부족' if pd.isna(row['mean_interval']) else f"{row['mean_interval']:g}회"
    st.write(f"완전 관측 구간의 평균 출현 간격 {interval} · 유효 간격 {row['valid_interval_count']}건 · 제외 간격 {row['excluded_interval_count']}건")
    st.write(f"다음 회차 본번호 등장 {row['next_main_hits']}/{row['next_main_observed']}건 · 관측 미완료 {row['next_main_pending']}건")
    value = '자료 없음' if not row['valid_prize_events'] else f"{_won_to_eok(row['second_prize_total']):,.2f}억 원"
    st.metric('보너스 등장 회차의 2등 총액 합계', value)
    st.caption(f"공시 당첨금 기준·세전 · 금액 유효 {row['valid_prize_events']}회 · 금액 제외 {row['excluded_prize_events']}회")
    st.write('번호별 보너스 기록')
    summary = result['summary'].sort_values('bonus_count', ascending=False, kind='stable')
    display = summary[['번호', 'bonus_count', 'bonus_rate', 'main_count', 'main_rate',
                       'last_bonus_round', 'rounds_since_bonus', 'mean_interval']].rename(columns={
        'bonus_count': '보너스 출현', 'bonus_rate': '보너스 출현률 (%)',
        'main_count': '본번호 출현', 'main_rate': '본번호 출현률 (%)',
        'last_bonus_round': '마지막 보너스 회차', 'rounds_since_bonus': '경과 회차',
        'mean_interval': '평균 간격 (회)'})
    st.dataframe(display, hide_index=True, width='stretch')
    coverage = result['coverage']
    st.caption(f"보너스 관측 {coverage['valid_bonus_rounds']}회 · 본번호 관측 {coverage['observed_rounds']}회 · "
               f"미관측 회차 {coverage['missing_rounds']}건 · 보너스 결측 {coverage['missing_bonus_rounds']}건")
    with st.expander('보너스 등장 회차·2등 금액·후속 기록'):
        events = result['events'].loc[result['events']['번호'].eq(number)].rename(columns={
            'next_round': '다음 회차', 'next_main_observed': '다음 회차 관측',
            'next_main_hit': '다음 회차 본번호 등장', 'second_per_game': '2등 게임당 금액 (원)',
            'second_winning_games': '2등 당첨게임 수', 'second_amount': '2등 총액 (원)',
            'second_exclusion_reason': '금액 제외 사유', 'second_amount_source': '금액 산출 근거'})
        st.dataframe(events, hide_index=True, width='stretch')

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
    elif view == '당첨금 배분':
        _render_prizes(history)
    else:
        _render_bonus(history)
    _sources()
