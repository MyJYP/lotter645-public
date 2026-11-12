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
    st.radio('보기', ['출현 흐름', '당첨금 배분', '보너스 번호'],
             horizontal=True, key='number_trend_view')
    _sources()
