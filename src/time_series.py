"""
시계열 분석 모듈
"""
import pandas as pd
import numpy as np
from collections import Counter, defaultdict
from numbers import Integral, Real
from decimal import Decimal, InvalidOperation
from fractions import Fraction

from data_loader import normalize_draw_history


def validate_trend_numbers(frame):
    """Validate number history and return an independent copy oldest first."""
    required = {'회차', '당첨번호', '보너스번호'}
    if not required.issubset(frame.columns):
        raise ValueError('회차·당첨번호·보너스번호 컬럼이 필요합니다.')
    if frame['회차'].map(lambda value: isinstance(value, (bool, np.bool_))).any():
        raise ValueError('회차는 양의 정수여야 합니다.')
    try:
        result = normalize_draw_history(frame)
    except TypeError as error:
        raise ValueError('본번호는 1~45의 서로 다른 정수 6개여야 합니다.') from error

    bonuses = []
    for numbers, bonus in zip(result['당첨번호'], result['보너스번호']):
        if bonus is None or bonus is pd.NA:
            bonuses.append(pd.NA)
            continue
        if not isinstance(bonus, Real) or isinstance(bonus, (bool, np.bool_)):
            raise ValueError('보너스번호는 1~45의 정수여야 합니다.')
        if pd.isna(bonus):
            bonuses.append(pd.NA)
            continue
        if not np.isfinite(bonus) or bonus % 1 or not 1 <= bonus <= 45:
            raise ValueError('보너스번호는 1~45의 정수여야 합니다.')
        if bonus in numbers:
            raise ValueError('보너스번호는 본번호와 중복될 수 없습니다.')
        bonuses.append(int(bonus))

    result['보너스번호'] = pd.array(bonuses, dtype='Int64')
    return result.sort_values('회차').reset_index(drop=True)


def _parse_prize_integer(value):
    """Return an exact nonnegative integer and its exclusion reason."""
    if value is None or value is pd.NA:
        return pd.NA, '자료 없음'
    if isinstance(value, (bool, np.bool_)):
        return pd.NA, '비음수 정수 필요'
    try:
        number = Decimal(str(value).replace(',', '').strip())
    except InvalidOperation:
        return pd.NA, '숫자 형식 오류'
    if number.is_nan():
        return pd.NA, '자료 없음'
    if not number.is_finite() or number < 0 or number != number.to_integral_value():
        return pd.NA, '비음수 정수 필요'
    return int(number), ''


def prepare_trend_data(numbers_df, prizes_df):
    """Join validated number history to exact prize values by draw number."""
    # A completely empty input is valid; missing columns on populated input are not.
    if numbers_df.empty and len(numbers_df.columns) == 0:
        numbers_df = numbers_df.reindex(columns=['회차', '당첨번호', '보너스번호'])
    if prizes_df.empty and len(prizes_df.columns) == 0:
        prizes_df = prizes_df.reindex(columns=['회차'])
    history = validate_trend_numbers(numbers_df)
    history['일자'] = pd.to_datetime(
        history['일자'] if '일자' in history else pd.Series(pd.NaT, index=history.index),
        errors='coerce', format='mixed',
    ).astype('datetime64[ns]')
    history = history[['회차', '일자', '당첨번호', '보너스번호']]
    history['당첨번호'] = history['당첨번호'].astype(object)
    if '회차' not in prizes_df:
        raise ValueError('당첨금 자료에 회차 컬럼이 필요합니다.')
    if prizes_df['회차'].map(lambda value: isinstance(value, (bool, np.bool_))).any():
        raise ValueError('회차는 양의 정수여야 합니다.')
    columns = ['1등 당첨액', '1등 당첨자수', '2등 당첨액', '2등 당첨자수']
    prizes = normalize_draw_history(prizes_df.reindex(columns=['회차', *columns]))
    # Keep Python integers as objects so missing rows cannot coerce them to float.
    # The right-hand values must also be objects before a missing-row join.
    for column in columns:
        parsed = [_parse_prize_integer(value) for value in prizes[column]]
        prizes[column] = pd.Series([value for value, _ in parsed], dtype=object)
        prizes[f'{column} 제외 사유'] = [reason for _, reason in parsed]
    history = history.drop(columns=columns, errors='ignore')
    result = history.merge(prizes, on='회차', how='left', validate='one_to_one', sort=False)
    for column in columns:
        result[f'{column} 제외 사유'] = result[f'{column} 제외 사유'].astype(object).fillna('회차 금액 자료 없음')
        result[column] = result[column].where(result[column].notna(), pd.NA)
    # Keep one schema, including dtypes, for empty and populated histories.
    for column in columns:
        result[column] = result[column].astype(object)
        result[f'{column} 제외 사유'] = result[f'{column} 제외 사유'].astype(object)
    return result[['회차', '일자', '당첨번호', '보너스번호', *columns,
                   *[f'{column} 제외 사유' for column in columns]]].reset_index(drop=True)


def summarize_trend_coverage(history):
    """Describe prepared observed history without filling missing draws with zeros."""
    if history.empty:
        return {
            'start_round': None, 'end_round': None, 'last_draw_date': pd.NaT,
            'observed_rounds': 0, 'missing_rounds': 0, 'missing_bonus_rounds': 0,
        }
    start = int(history['회차'].min())
    end = int(history['회차'].max())
    latest = history.loc[history['회차'].eq(end)].iloc[0]
    return {
        'start_round': start,
        'end_round': end,
        'last_draw_date': latest['일자'],
        'observed_rounds': len(history),
        'missing_rounds': end - start + 1 - len(history),
        'missing_bonus_rounds': int(history['보너스번호'].isna().sum()),
    }


def build_appearance(history, kind='main', recent_rounds=None):
    """Return full-history appearance indicators and complete-window rates.

    Missing draws (and missing bonus observations in bonus mode) invalidate
    every rolling window containing them. Rates are percentages, not forecasts.
    Cross events use consecutive valid 5/20-round windows. Optional range
    selection happens after calculation, retaining earlier warm-up history.
    """
    if kind not in ('main', 'bonus'):
        raise ValueError('kind는 main 또는 bonus여야 합니다.')
    if recent_rounds is not None and (
            isinstance(recent_rounds, (bool, np.bool_)) or
            not isinstance(recent_rounds, Integral) or recent_rounds <= 0):
        raise ValueError('recent_rounds는 양의 정수 또는 None이어야 합니다.')
    windows = (5, 10, 20, 60, 120)
    result = pd.DataFrame({
        '회차': pd.Series(dtype='int64'),
        '번호': pd.Series(dtype='int64'),
        'appeared': pd.Series(dtype='float64'),
        **{f'count_{n}': pd.Series(dtype='float64') for n in windows},
        **{f'ma_{n}': pd.Series(dtype='float64') for n in windows},
        'cross': pd.Series(dtype='string'),
    })
    if history.empty:
        return result

    observed = validate_trend_numbers(history)
    start = int(observed['회차'].iloc[0])
    end = int(observed['회차'].iloc[-1])
    rounds = np.arange(start, end + 1, dtype=np.int64)
    matrix = np.full((len(rounds), 45), np.nan)
    for draw, numbers, bonus in zip(
            observed['회차'], observed['당첨번호'], observed['보너스번호']):
        if kind == 'bonus' and pd.isna(bonus):
            continue
        row = int(draw) - start
        matrix[row, :] = 0
        selected = numbers if kind == 'main' else [int(bonus)]
        matrix[row, np.asarray(selected, dtype=int) - 1] = 1

    result = pd.DataFrame({
        '회차': np.repeat(rounds, 45),
        '번호': np.tile(np.arange(1, 46, dtype=np.int64), len(rounds)),
        'appeared': matrix.ravel(),
    })
    indicators = pd.DataFrame(matrix)
    for n in windows:
        counts = indicators.rolling(n, min_periods=n).sum().to_numpy().ravel()
        result[f'count_{n}'] = counts
        result[f'ma_{n}'] = counts * 100 / n
    difference = 4 * result['count_5'] - result['count_20']
    previous = difference.groupby(result['번호']).shift()
    valid = difference.notna() & previous.notna()
    result['cross'] = pd.Series(pd.NA, index=result.index, dtype='string')
    result.loc[valid, 'cross'] = 'none'
    result.loc[valid & previous.le(0) & difference.gt(0), 'cross'] = 'up'
    result.loc[valid & previous.ge(0) & difference.lt(0), 'cross'] = 'down'
    if recent_rounds is not None:
        result = result.loc[result['회차'].ge(max(start, end - int(recent_rounds) + 1))]
    return result[['회차', '번호', 'appeared',
                   *[f'count_{n}' for n in windows],
                   *[f'ma_{n}' for n in windows], 'cross']].reset_index(drop=True)


def prepare_prize_rounds(history, basis='total', rank=1):
    """Resolve exact per-draw amounts from prepared history for ranks 1 or 2."""
    if basis not in ('total', 'per_game'):
        raise ValueError('basis는 total 또는 per_game이어야 합니다.')
    if isinstance(rank, (bool, np.bool_)) or not isinstance(rank, Integral) or rank not in (1, 2):
        raise ValueError('rank는 1 또는 2여야 합니다.')
    amount_column = f'{rank}등 당첨액'
    games_column = f'{rank}등 당첨자수'
    required = ['회차', amount_column, games_column]
    if not set(required).issubset(history.columns):
        raise ValueError('준비된 회차·당첨금·당첨게임 수 컬럼이 필요합니다.')
    reason_columns = [f'{amount_column} 제외 사유', f'{games_column} 제외 사유']
    rounds = normalize_draw_history(
        history.reindex(columns=[*required, *reason_columns]),
    ).sort_values('회차').reset_index(drop=True)
    per_game_values, game_counts, amounts, reasons, sources = [], [], [], [], []
    for raw_amount, raw_games, saved_amount_reason, saved_games_reason in zip(
            rounds[amount_column], rounds[games_column],
            rounds[reason_columns[0]], rounds[reason_columns[1]]):
        per_game, amount_reason = _parse_prize_integer(raw_amount)
        games, games_reason = _parse_prize_integer(raw_games)
        if isinstance(saved_amount_reason, str) and saved_amount_reason:
            amount_reason = saved_amount_reason
        if isinstance(saved_games_reason, str) and saved_games_reason:
            games_reason = saved_games_reason
        amount = pd.NA
        reason = ''
        source = '검증 제외'
        if games_reason:
            reason = f'{games_column}: {games_reason}'
        elif games == 0:
            amount = 0
            source = '당첨게임 없음'
        elif amount_reason:
            reason = f'{amount_column}: {amount_reason}'
        elif basis == 'total':
            amount = per_game * games
            source = '게임당 당첨금 × 당첨게임 수'
        else:
            amount = per_game
            source = '공시 게임당 당첨금'
        per_game_values.append(per_game)
        game_counts.append(games)
        amounts.append(amount)
        reasons.append(reason)
        sources.append(source)
    return pd.DataFrame({
        '회차': rounds['회차'],
        'per_game': pd.Series(per_game_values, dtype=object),
        'winning_games': pd.Series(game_counts, dtype=object),
        'amount': pd.Series(amounts, dtype=object),
        'exclusion_reason': pd.Series(reasons, dtype=object),
        'amount_source': pd.Series(sources, dtype=object),
    })


def _resolve_round_bounds(history, start, end):
    """Resolve optional inclusive round bounds on validated history."""
    for name, value in (('start', start), ('end', end)):
        if value is not None and (
                isinstance(value, (bool, np.bool_)) or
                not isinstance(value, Integral) or value <= 0):
            raise ValueError(f'{name}는 양의 정수 또는 None이어야 합니다.')
    if not history.empty:
        start = int(history['회차'].min()) if start is None else int(start)
        end = int(history['회차'].max()) if end is None else int(end)
    if start is not None and end is not None and start > end:
        raise ValueError('start는 end 이하이어야 합니다.')
    return start, end


def build_prize_allocation(history, start=None, end=None, basis='total'):
    """Allocate selected first-prize amounts exactly, keeping a denominator of six."""
    observed = validate_trend_numbers(history)
    start, end = _resolve_round_bounds(observed, start, end)
    prizes = prepare_prize_rounds(observed, basis=basis)
    selected_rounds = range(start, end + 1) if start is not None and end is not None else range(0)
    number_lookup = observed.set_index('회차')['당첨번호'].to_dict()
    amount_lookup = prizes.set_index('회차')['amount'].to_dict()
    totals = [0] * 46
    appearances = [0] * 46
    valid_appearances = [0] * 46
    rows = []
    for draw in selected_rounds:
        numbers = set(number_lookup.get(draw, ()))
        amount = amount_lookup.get(draw, pd.NA)
        valid = not pd.isna(amount)
        for number in range(1, 46):
            appeared = number in numbers
            allocation = int(amount) * int(appeared) if valid else pd.NA
            appearances[number] += int(appeared)
            valid_appearances[number] += int(valid and appeared)
            if valid:
                totals[number] += allocation
            rows.append((draw, number, allocation, totals[number]))
    series = pd.DataFrame(rows, columns=[
        '회차', '번호', 'allocation_numerator', 'cumulative_numerator',
    ], dtype=object)
    series = series.astype({'회차': 'int64', '번호': 'int64'})
    summary = pd.DataFrame([
        (number, totals[number], appearances[number], valid_appearances[number],
         Fraction(totals[number], 6 * valid_appearances[number])
         if valid_appearances[number] else pd.NA)
        for number in range(1, 46)
    ], columns=['번호', 'cumulative_numerator', 'appearance_count',
                'valid_appearance_count', 'average_allocation'], dtype=object)
    summary = summary.astype({'번호': 'int64', 'appearance_count': 'int64',
                              'valid_appearance_count': 'int64'})
    details = prizes.merge(
        observed[['회차', '일자', '당첨번호']], on='회차', validate='one_to_one',
    ).set_index('회차').reindex(selected_rounds)
    details.index.name = '회차'
    observed_mask = details.index.isin(observed['회차'])
    details['exclusion_reason'] = details['exclusion_reason'].fillna('관측 회차 없음')
    details['amount_source'] = details['amount_source'].fillna('관측 회차 없음')
    for column in ('per_game', 'winning_games', 'amount', '당첨번호'):
        details[column] = details[column].where(details[column].notna(), pd.NA)
    valid_mask = details['amount'].notna()
    coverage = {
        'start_round': start,
        'end_round': end,
        'basis': basis,
        'observed_rounds': int(observed_mask.sum()),
        'missing_rounds': len(selected_rounds) - int(observed_mask.sum()),
        'valid_prize_rounds': int(valid_mask.sum()),
        'excluded_prize_rounds': int((observed_mask & ~valid_mask).sum()),
        'total_amount': sum(details.loc[valid_mask, 'amount']),
    }
    return {'series': series, 'summary': summary,
            'rounds': details.reset_index(), 'coverage': coverage}


def summarize_bonus(history, start=None, end=None):
    """Summarize bonus observations with explicit valid-data denominators."""
    observed = validate_trend_numbers(history)
    start, end = _resolve_round_bounds(observed, start, end)
    selected = observed
    if start is not None:
        selected = selected.loc[selected['회차'].ge(start)]
    if end is not None:
        selected = selected.loc[selected['회차'].le(end)]
    valid_bonus = selected.loc[selected['보너스번호'].notna()]
    known_rounds = set(valid_bonus['회차'])
    rows = []
    for number in range(1, 46):
        appearances = valid_bonus.loc[valid_bonus['보너스번호'].eq(number), '회차'].tolist()
        intervals = []
        excluded_intervals = 0
        for before, after in zip(appearances, appearances[1:]):
            if all(draw in known_rounds for draw in range(before, after + 1)):
                intervals.append(after - before)
            else:
                excluded_intervals += 1
        main_count = sum(number in numbers for numbers in selected['당첨번호'])
        rows.append((number, len(appearances),
                     len(appearances) * 100 / len(valid_bonus) if len(valid_bonus) else pd.NA,
                     main_count, main_count * 100 / len(selected) if len(selected) else pd.NA,
                     int(appearances[-1]) if appearances else pd.NA,
                     int(end - appearances[-1]) if appearances else pd.NA,
                     sum(intervals) / len(intervals) if intervals else pd.NA,
                     len(intervals), excluded_intervals))
    summary = pd.DataFrame(rows, columns=[
        '번호', 'bonus_count', 'bonus_rate', 'main_count', 'main_rate',
        'last_bonus_round', 'rounds_since_bonus', 'mean_interval',
        'valid_interval_count', 'excluded_interval_count',
    ], dtype=object)
    summary = summary.astype({column: 'int64' for column in [
        '번호', 'bonus_count', 'main_count', 'valid_interval_count', 'excluded_interval_count']})
    events = valid_bonus[['회차', '보너스번호']].rename(columns={'보너스번호': '번호'}).reset_index(drop=True)
    main_lookup = selected.set_index('회차')['당첨번호'].to_dict()
    next_observed, next_hits = [], []
    for draw, number in zip(events['회차'], events['번호']):
        next_numbers = main_lookup.get(int(draw) + 1)
        available = next_numbers is not None
        next_observed.append(available)
        next_hits.append(int(number) in next_numbers if available else pd.NA)
    events['next_round'] = events['회차'] + 1
    events['next_main_observed'] = pd.Series(next_observed, dtype=bool)
    events['next_main_hit'] = pd.Series(next_hits, dtype='boolean')
    for column in ('next_main_observed', 'next_main_hit'):
        counts = events.groupby('번호')[column].sum()
        target = 'next_main_hits' if column == 'next_main_hit' else 'next_main_observed'
        summary[target] = summary['번호'].map(counts).fillna(0).astype('int64')
    summary['next_main_pending'] = summary['bonus_count'] - summary['next_main_observed']
    summary['next_main_rate'] = pd.Series([
        hits * 100 / count if count else pd.NA
        for hits, count in zip(summary['next_main_hits'], summary['next_main_observed'])
    ], dtype=object)
    financial_input = selected.copy()
    for column in ('2등 당첨액', '2등 당첨자수'):
        if column not in financial_input:
            financial_input[column] = pd.NA
    financial = prepare_prize_rounds(financial_input, rank=2).rename(columns={
        column: f'second_{column}' for column in (
            'per_game', 'winning_games', 'amount', 'exclusion_reason', 'amount_source')})
    events = events.merge(financial, on='회차', how='left', validate='one_to_one')
    second_totals, valid_events, excluded_events = [], [], []
    for number in range(1, 46):
        amounts = events.loc[events['번호'].eq(number), 'second_amount']
        second_totals.append(sum(amounts.dropna()))
        valid_events.append(int(amounts.notna().sum()))
        excluded_events.append(int(amounts.isna().sum()))
    summary['second_prize_total'] = pd.Series(second_totals, dtype=object)
    summary['valid_prize_events'] = valid_events
    summary['excluded_prize_events'] = excluded_events
    expected = end - start + 1 if start is not None and end is not None else 0
    return {
        'summary': summary,
        'events': events,
        'coverage': {'start_round': start, 'end_round': end,
                     'observed_rounds': len(selected), 'missing_rounds': expected - len(selected),
                     'valid_bonus_rounds': len(valid_bonus),
                     'missing_bonus_rounds': len(selected) - len(valid_bonus),
                     'pending_next_main_events': int(summary['next_main_pending'].sum()),
                     'excluded_second_prize_events': sum(excluded_events)},
    }


class TimeSeriesAnalysis:
    """시계열 분석 클래스"""

    def __init__(self, data_loader):
        """
        Args:
            data_loader: LottoDataLoader 인스턴스
        """
        self.loader = data_loader
        self.df = data_loader.df
        self.numbers_df = data_loader.numbers_df

    def recent_hot_cold_numbers(self, recent_rounds=50, top_n=10):
        """최근 핫넘버/콜드넘버 분석"""
        print("\n" + "="*60)
        print(f"1. 최근 {recent_rounds}회차 핫넘버/콜드넘버 분석")
        print("="*60)

        # 최근 N회차 데이터
        recent_data = self.numbers_df.head(recent_rounds)

        all_numbers = []
        for _, row in recent_data.iterrows():
            all_numbers.extend(row['당첨번호'])

        frequency = Counter(all_numbers)

        # 모든 번호(1-45) 초기화
        all_45_numbers = {i: 0 for i in range(1, 46)}
        all_45_numbers.update(frequency)

        freq_df = pd.DataFrame(
            sorted(all_45_numbers.items(), key=lambda x: x[1], reverse=True),
            columns=['번호', '출현횟수']
        )

        freq_df['출현율(%)'] = (freq_df['출현횟수'] / recent_rounds * 100).round(2)

        print(f"\n🔥 핫넘버 TOP {top_n} (최다 출현):")
        print(freq_df.head(top_n).to_string(index=False))

        print(f"\n❄️  콜드넘버 TOP {top_n} (최소 출현):")
        print(freq_df.tail(top_n).to_string(index=False))

        return freq_df

    def number_appearance_interval(self, number):
        """특정 번호의 출현 간격 분석"""
        print("\n" + "="*60)
        print(f"2. 번호 {number}의 출현 간격 분석")
        print("="*60)

        appearance_rounds = []

        for idx, row in self.numbers_df.iterrows():
            if number in row['당첨번호'] or number == row['보너스번호']:
                appearance_rounds.append(row['회차'])

        if not appearance_rounds:
            print(f"\n번호 {number}는 출현 기록이 없습니다.")
            return None

        # 출현 간격 계산
        intervals = []
        for i in range(len(appearance_rounds) - 1):
            interval = appearance_rounds[i] - appearance_rounds[i+1]
            intervals.append(interval)

        if intervals:
            interval_stats = {
                '총 출현 횟수': len(appearance_rounds),
                '평균 간격': round(np.mean(intervals), 2),
                '최소 간격': min(intervals),
                '최대 간격': max(intervals),
                '표준편차': round(np.std(intervals), 2) if len(intervals) > 1 else 0
            }

            stats_df = pd.DataFrame([interval_stats])
            print("\n" + stats_df.to_string(index=False))

            # 최근 출현 정보
            latest_round = appearance_rounds[0]
            current_round = self.numbers_df.iloc[0]['회차']
            rounds_since = int(current_round - latest_round)

            print(f"\n최근 출현: {latest_round}회차")
            print(f"미출현 기간: {rounds_since}회")

            return stats_df, appearance_rounds
        else:
            print(f"\n번호 {number}는 1회만 출현했습니다.")
            return None

    def long_missing_numbers(self, top_n=10):
        """장기 미출현 번호 분석"""
        print("\n" + "="*60)
        print(f"3. 장기 미출현 번호 TOP {top_n}")
        print("="*60)

        current_round = self.numbers_df.iloc[0]['회차']
        last_appearance = {}

        # 모든 번호의 최근 출현 회차 찾기
        for num in range(1, 46):
            for idx, row in self.numbers_df.iterrows():
                if num in row['당첨번호'] or num == row['보너스번호']:
                    last_appearance[num] = row['회차']
                    break

            # 한 번도 출현하지 않은 경우
            if num not in last_appearance:
                last_appearance[num] = 0

        # 미출현 기간 계산
        missing_periods = {
            num: int(current_round - last_round)
            for num, last_round in last_appearance.items()
        }

        # 정렬
        sorted_missing = sorted(
            missing_periods.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]

        missing_df = pd.DataFrame(
            sorted_missing,
            columns=['번호', '미출현회차']
        )

        missing_df['최근출현'] = missing_df['번호'].map(last_appearance)

        print("\n" + missing_df.to_string(index=False))

        return missing_df

    def rolling_frequency(self, window_size=100):
        """이동 평균 빈도 분석 (특정 번호들의 트렌드)"""
        print("\n" + "="*60)
        print(f"4. 이동 평균 빈도 분석 (윈도우: {window_size}회)")
        print("="*60)

        # 번호별 이동 평균 계산
        number_trends = defaultdict(list)

        total_rounds = len(self.numbers_df)

        for i in range(0, total_rounds - window_size + 1, 10):  # 10회차씩 이동
            window_data = self.numbers_df.iloc[i:i+window_size]

            all_numbers = []
            for _, row in window_data.iterrows():
                all_numbers.extend(row['당첨번호'])

            frequency = Counter(all_numbers)

            for num in range(1, 46):
                number_trends[num].append(frequency.get(num, 0))

        # 최근 트렌드 상승 번호 찾기
        trend_changes = {}
        for num, trends in number_trends.items():
            if len(trends) >= 2:
                recent_avg = np.mean(trends[:3]) if len(trends) >= 3 else trends[0]
                old_avg = np.mean(trends[-3:]) if len(trends) >= 3 else trends[-1]
                trend_changes[num] = recent_avg - old_avg

        # 상승세 TOP 10
        rising = sorted(
            trend_changes.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        rising_df = pd.DataFrame(
            rising,
            columns=['번호', '트렌드변화']
        )

        print("\n📈 상승세 번호 TOP 10:")
        print(rising_df.to_string(index=False))

        # 하락세 TOP 10
        falling = sorted(
            trend_changes.items(),
            key=lambda x: x[1]
        )[:10]

        falling_df = pd.DataFrame(
            falling,
            columns=['번호', '트렌드변화']
        )

        print("\n📉 하락세 번호 TOP 10:")
        print(falling_df.to_string(index=False))

        return rising_df, falling_df

    def run_all(self):
        """모든 시계열 분석 실행"""
        print("\n\n" + "📊 "*20)
        print("시계열 분석 시작")
        print("📊 "*20 + "\n")

        hot_cold_50 = self.recent_hot_cold_numbers(recent_rounds=50)
        hot_cold_100 = self.recent_hot_cold_numbers(recent_rounds=100)
        missing = self.long_missing_numbers(top_n=10)
        rising, falling = self.rolling_frequency(window_size=100)

        print("\n\n" + "✅ "*20)
        print("시계열 분석 완료")
        print("✅ "*20 + "\n")

        return {
            'hot_cold_50': hot_cold_50,
            'hot_cold_100': hot_cold_100,
            'missing_numbers': missing,
            'rising_trend': rising,
            'falling_trend': falling
        }
