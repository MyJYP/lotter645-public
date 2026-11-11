"""Session-isolated UI for 사용자 패턴 선호도 점수 (Pattern Preference Score)."""
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import streamlit as st
from pattern_preference import PatternConfig, PatternPreferenceEngine

LABELS = {'pair': '동반/상극 쌍', 'sequence': '연속수·이월수·주기', 'zone': '구간 분포', 'grid': '용지 그리드'}


def render_pattern_preference(history):
    st.subheader('다각도 패턴 분석 · 1세트 연속 추출')
    st.caption('사용자 패턴 선호도 점수(Pattern Preference Score)는 과거 패턴과 설정에 대한 적합도이며 당첨확률이 아닙니다.')
    if 'pattern_draw_history' not in st.session_state:
        st.session_state.pattern_draw_history = []
    if 'pattern_rng' not in st.session_state:
        st.session_state.pattern_rng = np.random.default_rng()
    st.caption(f"사용 가능한 과거 자료: {int(history['회차'].min())}~{int(history['회차'].max())}회 · {len(history)}개 회차")
    with st.expander('패턴 가중치 및 패턴 필터 조건', expanded=True):
        weights = tuple(st.slider(label + ' 가중치', 0, 100, 25, key='pattern_weight_' + name)
                        for name, label in LABELS.items())
        lookback = st.selectbox('분석 기간 (0은 보유 자료 전체)', [0, 20, 100, 200, 500], key='pattern_lookback')
        recent = st.selectbox('최근 패턴 관측 회차 수', [10, 20, 50], index=1, key='pattern_recent')
        quantile = st.slider('상극 쌍: 저빈도 기준 분위수 (%)', 0, 20, 5, key='pattern_quantile') / 100
        st.caption('상극 쌍은 분석 기간 내 미관측 또는 저빈도 쌍을 뜻합니다. 관측 부족 시 조건 완화가 발생할 수 있습니다.')
        pair_filter = st.checkbox('상극 쌍 제외', value=True, key='pattern_pair_filter')
        zone_filter = st.checkbox('구간 집중 제한', value=True, key='pattern_zone_filter')
        grid_filter = st.checkbox('그리드 열 집중·모서리 군집 제한', value=True, key='pattern_grid_filter')
        zone_choice = st.selectbox('구간 목표 (1~9 / 10~19 / 20~29 / 30~39 / 40~45)',
                                  ['과거 관측 분포', '1:2:1:1:1', '1:1:2:1:1'], key='pattern_zone_target')
        temperature = st.slider('상위 풀 내 선택 다양성 (온도)', 0.5, 20.0, 5.0, key='pattern_temperature')
    if st.button('추출 이력 초기화', key='pattern_clear'):
        st.session_state.pattern_draw_history = []
    if st.button('다각도 패턴 분석 1세트 새로 뽑기', type='primary', key='pattern_generate'):
        try:
            config = PatternConfig(weights=weights, lookback=lookback, recent_window=recent,
                                   anti_pair_quantile=quantile, temperature=temperature,
                                   pair_filter=pair_filter, zone_filter=zone_filter, grid_filter=grid_filter,
                                   zone_target=None if zone_choice == '과거 관측 분포' else tuple(map(int, zone_choice.split(':'))))
            with st.spinner('패턴 점수와 필터 조건을 계산하고 있습니다...'):
                engine = PatternPreferenceEngine(history, config)
                seen = [row['numbers'] for row in st.session_state.pattern_draw_history]
                result = engine.draw(seen=seen, rng=st.session_state.pattern_rng)
                result['created_at'] = datetime.now(timezone.utc).isoformat()
                st.session_state.pattern_draw_history.append(result)
        except ValueError as exc:
            st.error(str(exc))
    if not st.session_state.pattern_draw_history:
        return
    result = st.session_state.pattern_draw_history[-1]
    st.markdown('### ' + ' · '.join(str(n) for n in result['numbers']))
    st.metric('사용자 패턴 선호도 점수(Pattern Preference Score)', f"{result['score']:.2f} / 100")
    st.caption(f"이번 후보 {result['candidate_count']}개 · 통과 {result['eligible_count']}개 · 선택 풀 {result['pool_size']}개. "
               '상위 풀은 이번 탐색 후보 내 순위이며 전체 조합의 순위가 아닙니다.')
    st.caption(f"이 결과의 분석 범위: {result['data_range'][0]}~{result['data_range'][1]}회 · "
               f"관측 {result['draw_count']}회 · 범위 내 누락 {result['missing_rounds']}회")
    if result['relaxations']:
        st.warning('패턴 필터 조건 완화: ' + ' → '.join(result['relaxations']))
    else:
        st.success('설정한 패턴 필터 조건을 모두 통과했습니다.')
    st.dataframe(pd.DataFrame([{'패턴': LABELS[name], '선호도 점수': value,
                               '가중 기여도': result['contributions'][name]} for name, value in result['groups'].items()]),
                 hide_index=True)
    with st.expander('패턴 계산 근거 및 필터 완화 내역'):
        st.json({'특징': result['features'], '원래 조건 위반': result['violations'],
                 '단계별 후보': result['audits'], '결과 생성 시 설정': result['config']})
    st.subheader('이번 세션의 추출 이력')
    st.dataframe(pd.DataFrame([{'순서': i, '번호': ', '.join(map(str, row['numbers'])),
                               '패턴 선호도 점수': round(row['score'], 2),
                               '완화한 조건': ' → '.join(row['relaxations']) or '없음'}
                              for i, row in enumerate(st.session_state.pattern_draw_history, 1)]), hide_index=True)
