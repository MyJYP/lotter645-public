from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from data_loader import LottoDataLoader
from time_series import build_prize_allocation, build_appearance, prepare_prize_rounds, prepare_trend_data, summarize_trend_coverage, validate_trend_numbers


def history():
    return pd.DataFrame({
        '회차': [103, 101, 102],
        '당첨번호': [[1, 2, 3, 4, 5, 6]] * 3,
        '보너스번호': [pd.NA, 7, 8],
    }, index=[90, 20, 50])


def test_validation_sorts_preserves_missing_bonus_and_input():
    frame = history()
    before = frame.copy(deep=True)
    result = validate_trend_numbers(frame)
    assert result['회차'].tolist() == [101, 102, 103]
    assert result.index.tolist() == [0, 1, 2]
    assert result['보너스번호'].iloc[:2].tolist() == [7, 8]
    assert pd.isna(result['보너스번호'].iloc[2])
    pd.testing.assert_frame_equal(frame, before)


@pytest.mark.parametrize('rounds', [[101, 101, 102], [0, 101, 102],
                                   [1.5, 101, 102], [True, 101, 102],
                                   [None, 101, 102]])
def test_invalid_rounds(rounds):
    frame = history()
    frame['회차'] = rounds
    with pytest.raises(ValueError, match='회차'):
        validate_trend_numbers(frame)


@pytest.mark.parametrize('numbers', [None, [1, 2], [1, 2, 3, 4, 5, 5],
                                    [0, 2, 3, 4, 5, 6], [1, 2, 3, 4, 5, 46],
                                    [True, 2, 3, 4, 5, 6]])
def test_invalid_main_numbers(numbers):
    frame = history()
    frame.at[90, '당첨번호'] = numbers
    with pytest.raises(ValueError, match='본번호'):
        validate_trend_numbers(frame)


@pytest.mark.parametrize('bonus', [0, 46, 7.5, True, np.inf, '7', [7], 1])
def test_invalid_bonus(bonus):
    frame = history()
    frame.at[90, '보너스번호'] = bonus
    with pytest.raises(ValueError, match='보너스번호'):
        validate_trend_numbers(frame)


def test_nullable_float_bonus_from_dataframe():
    frame = history()
    frame['보너스번호'] = [np.nan, 7.0, 8.0]
    result = validate_trend_numbers(frame)
    assert str(result['보너스번호'].dtype) == 'Int64'
    assert result['보너스번호'].iloc[:2].tolist() == [7, 8]
    assert pd.isna(result['보너스번호'].iloc[2])


def test_prizes_join_by_round_without_losing_integer_precision():
    prizes = pd.DataFrame({
        '회차': [103, 101],
        '1등 당첨액': ['9,007,199,254,740,993', '12000000000'],
        '1등 당첨자수': [2, 1],
        '2등 당첨액': [50000000, 0],
        '2등 당첨자수': [10, 0],
    })
    before = prizes.copy(deep=True)
    result = prepare_trend_data(history(), prizes).set_index('회차')
    assert result.index.tolist() == [101, 102, 103]
    assert result.at[103, '1등 당첨액'] == 9007199254740993
    assert isinstance(result.at[103, '1등 당첨액'], int)
    assert result.at[101, '1등 당첨액'] == 12000000000
    assert result.at[101, '2등 당첨자수'] == 0
    assert result.at[101, '2등 당첨자수 제외 사유'] == ''
    assert pd.isna(result.at[102, '1등 당첨액'])
    assert result.at[102, '1등 당첨액 제외 사유'] == '회차 금액 자료 없음'
    pd.testing.assert_frame_equal(prizes, before)


@pytest.mark.parametrize('value', [True, -1, 1.5, np.inf, 'invalid', pd.NA])
@pytest.mark.parametrize('column', ['1등 당첨액', '1등 당첨자수'])
def test_invalid_prize_field_preserves_draw_and_reason(value, column):
    prizes = pd.DataFrame({'회차': [101], column: [value]})
    result = prepare_trend_data(history(), prizes).set_index('회차')
    assert len(result) == 3
    assert pd.isna(result.at[101, column])
    assert result.at[101, f'{column} 제외 사유']


@pytest.mark.parametrize('rounds', [[101, 101], [True, 102], [0, 102]])
def test_invalid_prize_draw_keys(rounds):
    with pytest.raises(ValueError, match='회차'):
        prepare_trend_data(history(), pd.DataFrame({'회차': rounds}))



@pytest.mark.parametrize('empty_numbers', [pd.DataFrame(), history().iloc[:0]])
@pytest.mark.parametrize('empty_prizes', [pd.DataFrame(), pd.DataFrame(columns=['회차'])])
def test_empty_prepared_history_has_the_same_schema(empty_numbers, empty_prizes):
    empty = prepare_trend_data(empty_numbers, empty_prizes)
    populated = prepare_trend_data(history(), pd.DataFrame())
    assert empty.empty
    assert empty.columns.tolist() == populated.columns.tolist()
    assert empty.dtypes.to_dict() == populated.dtypes.to_dict()
    coverage = summarize_trend_coverage(empty)
    assert coverage['start_round'] is None and coverage['end_round'] is None
    assert pd.isna(coverage['last_draw_date'])
    assert coverage['observed_rounds'] == coverage['missing_rounds'] == 0
    assert coverage['missing_bonus_rounds'] == 0


def test_range_keeps_gaps_and_uses_last_round_date_not_last_known_date():
    numbers = history().loc[[90, 20]].copy()
    numbers['일자'] = ['invalid', '2026-01-03']
    before = numbers.copy(deep=True)
    prizes = pd.DataFrame({'회차': [104, 101], '1등 당첨액': [10, 20]})
    result = prepare_trend_data(numbers, prizes)
    coverage = summarize_trend_coverage(result)
    assert result['회차'].tolist() == [101, 103]
    assert coverage['start_round'] == 101
    assert coverage['end_round'] == 103
    assert coverage['observed_rounds'] == 2
    assert coverage['missing_rounds'] == 1
    assert coverage['missing_bonus_rounds'] == 1
    assert pd.isna(coverage['last_draw_date'])
    pd.testing.assert_frame_equal(numbers, before)
    reversed_result = prepare_trend_data(numbers.iloc[::-1], prizes.iloc[::-1])
    pd.testing.assert_frame_equal(result, reversed_result)


def test_one_round_coverage_and_missing_prizes():
    numbers = history().loc[[20]].copy()
    numbers['일자'] = ['2026-01-03']
    result = prepare_trend_data(numbers, pd.DataFrame())
    assert summarize_trend_coverage(result) == {
        'start_round': 101, 'end_round': 101,
        'last_draw_date': pd.Timestamp('2026-01-03'),
        'observed_rounds': 1, 'missing_rounds': 0, 'missing_bonus_rounds': 0,
    }
    assert result['1등 당첨액'].isna().all()
    assert result['1등 당첨액 제외 사유'].tolist() == ['회차 금액 자료 없음']


def test_missing_date_and_extra_columns_have_a_fixed_output_schema():
    numbers = history().assign(extra='unused')
    result = prepare_trend_data(numbers, pd.DataFrame())
    assert 'extra' not in result.columns
    assert result['일자'].isna().all()
    assert pd.isna(summarize_trend_coverage(result)['last_draw_date'])


def test_empty_numbers_do_not_inherit_prize_only_rounds():
    result = prepare_trend_data(pd.DataFrame(), pd.DataFrame({'회차': [999]}))
    assert result.empty
    assert summarize_trend_coverage(result)['end_round'] is None


def test_populated_inputs_still_require_draw_columns():
    with pytest.raises(ValueError, match='컬럼'):
        prepare_trend_data(pd.DataFrame({'other': [1]}), pd.DataFrame())
    with pytest.raises(ValueError, match='회차'):
        prepare_trend_data(history(), pd.DataFrame({'other': [1]}))



def appearance_history(length, kind='main', hits=()):
    return pd.DataFrame({
        '회차': range(1, length + 1),
        '당첨번호': [([1, 2, 3, 4, 5, 6] if t in hits else [2, 3, 4, 5, 6, 7])
                     if kind == 'main' else [2, 3, 4, 5, 6, 7]
                     for t in range(1, length + 1)],
        '보너스번호': [1 if kind == 'bonus' and t in hits else 45
                      for t in range(1, length + 1)],
    })


@pytest.mark.parametrize('kind', ['main', 'bonus'])
@pytest.mark.parametrize('window', [5, 10, 20, 60, 120])
def test_appearance_window_boundaries(kind, window):
    frame = appearance_history(window, kind, hits=[window])
    result = build_appearance(frame, kind).set_index(['회차', '번호'])
    assert pd.isna(result.at[(window - 1, 1), f'ma_{window}'])
    assert result.at[(window, 1), f'count_{window}'] == 1
    assert result.at[(window, 1), f'ma_{window}'] == pytest.approx(100 / window)
    assert result.at[(window, 44), f'ma_{window}'] == 0


@pytest.mark.parametrize('kind', ['main', 'bonus'])
def test_appearance_known_rates_and_all_number_rows(kind):
    result = build_appearance(appearance_history(20, kind, hits=[1, 18, 20]), kind)
    last = result[result['회차'] == 20].set_index('번호')
    assert last.index.tolist() == list(range(1, 46))
    assert len(result) == 20 * 45
    assert last.at[1, 'count_5'] == 2
    assert last.at[1, 'ma_5'] == 40
    assert last.at[1, 'count_20'] == 3
    assert last.at[1, 'ma_20'] == 15
    assert result.groupby('회차')['appeared'].sum().eq(6 if kind == 'main' else 1).all()


@pytest.mark.parametrize('kind', ['main', 'bonus'])
def test_missing_draw_invalidates_window_until_it_leaves(kind):
    frame = appearance_history(10, kind, hits=range(1, 11))
    frame = frame[frame['회차'] != 5]
    result = build_appearance(frame, kind)
    assert result.loc[result['회차'].eq(5), 'appeared'].isna().all()
    assert result.loc[result['회차'].between(5, 9), 'ma_5'].isna().all()
    assert result.loc[result['회차'].eq(10), 'ma_5'].notna().all()
    assert result.set_index(['회차', '번호']).at[(10, 1), 'ma_5'] == 100


def test_missing_bonus_only_invalidates_bonus_windows():
    frame = appearance_history(10)
    frame.loc[frame['회차'].eq(5), '보너스번호'] = np.nan
    bonus = build_appearance(frame, 'bonus')
    main = build_appearance(frame, 'main')
    assert bonus.loc[bonus['회차'].eq(5), 'appeared'].isna().all()
    assert bonus.loc[bonus['회차'].between(5, 9), 'ma_5'].isna().all()
    assert bonus.loc[bonus['회차'].eq(10), 'ma_5'].notna().all()
    assert main.loc[main['회차'].ge(5), 'ma_5'].notna().all()
    changed = frame.copy()
    changed['보너스번호'] = 44
    pd.testing.assert_frame_equal(main, build_appearance(changed, 'main'))


@pytest.mark.parametrize('kind', ['main', 'bonus'])
def test_appearance_order_index_input_immutability_and_no_future_effect(kind):
    frame = appearance_history(130, kind, hits=range(1, 131, 3))
    frame.index = np.arange(130) * 11
    before = frame.copy(deep=True)
    result = build_appearance(frame, kind)
    pd.testing.assert_frame_equal(result, build_appearance(frame.iloc[::-1], kind))
    past = build_appearance(frame[frame['회차'] <= 125], kind)
    pd.testing.assert_frame_equal(past, result[result['회차'] <= 125].reset_index(drop=True))
    pd.testing.assert_frame_equal(frame, before)


@pytest.mark.parametrize('kind', ['main', 'bonus'])
def test_empty_appearance_schema(kind):
    empty = build_appearance(prepare_trend_data(pd.DataFrame(), pd.DataFrame()), kind)
    full = build_appearance(appearance_history(1, kind), kind)
    assert empty.empty
    assert empty.dtypes.to_dict() == full.dtypes.to_dict()


def test_appearance_rejects_unknown_kind():
    with pytest.raises(ValueError, match='kind'):
        build_appearance(pd.DataFrame(), 'other')



@pytest.mark.parametrize('date_values', [
    None,
    [None, pd.NaT, None],
    ['2026-01-17', '2026-01-03', '2026-01-10'],
    pd.Series(pd.to_datetime(['2026-01-17', '2026-01-03', '2026-01-10'])).astype('datetime64[us]').array,
])
def test_prepared_schema_matches_empty_for_missing_and_valid_dates(date_values):
    frame = history()
    if date_values is not None:
        frame['일자'] = date_values
    before = frame.copy(deep=True)
    empty = prepare_trend_data(pd.DataFrame(), pd.DataFrame())
    actual = prepare_trend_data(frame, pd.DataFrame())
    assert actual.columns.tolist() == empty.columns.tolist()
    assert actual.dtypes.to_dict() == empty.dtypes.to_dict()
    assert str(actual['일자'].dtype) == 'datetime64[ns]'
    if date_values is None or all(pd.isna(value) for value in date_values):
        assert actual['일자'].isna().all()
    else:
        assert actual['일자'].tolist() == list(pd.date_range('2026-01-03', periods=3, freq='7D'))
    pd.testing.assert_frame_equal(frame, before)


def test_prepared_schema_matches_empty_for_actual_loader():
    loader = LottoDataLoader(Path(__file__).resolve().parents[1] / 'Data/645_251227.csv')
    loader.load_data()
    loader.preprocess()
    loader.extract_numbers()
    before = loader.numbers_df.copy(deep=True)
    empty = prepare_trend_data(pd.DataFrame(), pd.DataFrame())
    actual = prepare_trend_data(loader.numbers_df, loader.df)
    assert actual.columns.tolist() == empty.columns.tolist()
    assert actual.dtypes.to_dict() == empty.dtypes.to_dict()
    assert str(actual['일자'].dtype) == 'datetime64[ns]'
    expected_dates = loader.numbers_df.sort_values('회차')['일자'].astype('datetime64[ns]').reset_index(drop=True)
    pd.testing.assert_series_equal(actual['일자'], expected_dates)
    assert summarize_trend_coverage(actual)['last_draw_date'] == expected_dates.iloc[-1]
    pd.testing.assert_frame_equal(loader.numbers_df, before)


@pytest.mark.parametrize('reverse', [False, True])
def test_mixed_year_first_dates_are_parsed_independently(reverse):
    frame = appearance_history(5)
    frame['일자'] = ['2026-01-03', '2026.01.17', '2026/01/24', 'invalid', None]
    if reverse:
        frame = frame.iloc[::-1]
    actual = prepare_trend_data(frame, pd.DataFrame())
    assert str(actual['일자'].dtype) == 'datetime64[ns]'
    assert actual['일자'].iloc[:3].tolist() == [
        pd.Timestamp('2026-01-03'), pd.Timestamp('2026-01-17'), pd.Timestamp('2026-01-24'),
    ]
    assert actual['일자'].iloc[3:].isna().all()


@pytest.mark.parametrize('kind', ['main', 'bonus'])
def test_cross_events_and_missing_previous_window(kind):
    frame = appearance_history(40, kind, hits=[1, 2, 3, 4, 5, 21, 22, 23, 24, 25])
    result = build_appearance(frame, kind).set_index(['회차', '번호'])
    assert pd.isna(result.at[(20, 1), 'cross'])
    assert result.at[(21, 1), 'cross'] == 'none'
    assert result.at[(22, 1), 'cross'] == 'up'
    assert result.at[(23, 1), 'cross'] == 'none'
    assert result.at[(29, 1), 'cross'] == 'down'
    assert result.at[(21, 44), 'cross'] == 'none'


@pytest.mark.parametrize('hits,expected', [([1, 6, 11, 16, 21], 'none'),
                                          ([1, 6, 11, 16], 'down'),
                                          ([21], 'up')])
def test_cross_handles_equality(hits, expected):
    result = build_appearance(appearance_history(21, hits=hits)).set_index(['회차', '번호'])
    assert result.at[(21, 1), 'cross'] == expected


@pytest.mark.parametrize('kind', ['main', 'bonus'])
def test_range_selection_preserves_rates_and_first_visible_cross(kind):
    frame = appearance_history(40, kind, hits=[1, 2, 3, 4, 5, 21, 22, 23, 24, 25])
    full = build_appearance(frame, kind)
    recent = build_appearance(frame, kind, recent_rounds=19)
    pd.testing.assert_frame_equal(recent, full[full['회차'].ge(22)].reset_index(drop=True))
    assert recent.loc[recent['번호'].eq(1), 'cross'].iloc[0] == 'up'
    pd.testing.assert_frame_equal(full, build_appearance(frame, kind, recent_rounds=100))


def test_cross_recovery_requires_two_valid_windows_after_gap():
    frame = appearance_history(45)
    frame = frame[frame['회차'].ne(23)]
    result = build_appearance(frame).set_index(['회차', '번호'])
    assert pd.isna(result.at[(43, 1), 'cross'])
    assert result.at[(44, 1), 'cross'] == 'none'
    recent = build_appearance(frame, recent_rounds=23)
    assert recent['회차'].min() == 23
    assert recent.loc[recent['회차'].eq(23), 'appeared'].isna().all()


@pytest.mark.parametrize('value', [0, -1, True, 1.5, '20', np.nan])
def test_invalid_recent_rounds_are_rejected_even_for_empty_history(value):
    with pytest.raises(ValueError, match='recent_rounds'):
        build_appearance(pd.DataFrame(), recent_rounds=value)


def test_empty_cross_schema_matches_populated_result():
    empty = build_appearance(pd.DataFrame(), recent_rounds=50)
    full = build_appearance(appearance_history(1), recent_rounds=np.int64(50))
    assert empty.dtypes.to_dict() == full.dtypes.to_dict()


@pytest.mark.parametrize('basis,multiplier', [('total', 2), ('per_game', 1)])
@pytest.mark.parametrize('rank', [1, 2])
def test_prize_basis_exact_amount_and_source(basis, multiplier, rank):
    prizes = pd.DataFrame({'회차': [101], f'{rank}등 당첨액': ['9,007,199,254,740,993'],
                           f'{rank}등 당첨자수': [2]})
    prepared = prepare_trend_data(history().loc[[20]], prizes)
    before = prepared.copy(deep=True)
    result = prepare_prize_rounds(prepared, basis, rank)
    assert result.at[0, 'amount'] == 9007199254740993 * multiplier
    assert isinstance(result.at[0, 'amount'], int)
    assert result.at[0, 'exclusion_reason'] == ''
    assert result.at[0, 'amount_source'] == ('게임당 당첨금 × 당첨게임 수' if basis == 'total' else '공시 게임당 당첨금')
    pd.testing.assert_frame_equal(prepared, before)


@pytest.mark.parametrize('basis', ['total', 'per_game'])
@pytest.mark.parametrize('amount,games,expected,excluded', [
    (None, 0, 0, False), (100, 0, 0, False), (0, 3, 0, False),
    (None, 3, None, True), (100, None, None, True),
    (-1, 3, None, True), (100, 1.5, None, True),
])
def test_prize_zero_and_excluded_amounts(basis, amount, games, expected, excluded):
    prizes = pd.DataFrame({'회차': [101], '1등 당첨액': [amount], '1등 당첨자수': [games]})
    prepared = prepare_trend_data(history().loc[[20]], prizes)
    result = prepare_prize_rounds(prepared, basis)
    assert bool(result.at[0, 'exclusion_reason']) == excluded
    if excluded:
        assert pd.isna(result.at[0, 'amount'])
    else:
        assert result.at[0, 'amount'] == expected


def test_prize_missing_draw_order_and_empty_schema():
    prizes = pd.DataFrame({'회차': [103, 101], '1등 당첨액': [30, 10], '1등 당첨자수': [2, 1]})
    prepared = prepare_trend_data(history(), prizes)
    result = prepare_prize_rounds(prepared.iloc[::-1])
    assert result['회차'].tolist() == [101, 102, 103]
    assert result['amount'].iloc[[0, 2]].tolist() == [10, 60]
    assert pd.isna(result.at[1, 'amount'])
    assert result.at[1, 'exclusion_reason']
    empty = prepare_prize_rounds(prepare_trend_data(pd.DataFrame(), pd.DataFrame()))
    assert empty.empty
    assert empty.dtypes.to_dict() == result.dtypes.to_dict()


@pytest.mark.parametrize('options', [{'basis':'other'}, {'rank':3}, {'rank':True}, {'rank':1.5}])
def test_invalid_prize_options(options):
    prepared = prepare_trend_data(pd.DataFrame(), pd.DataFrame())
    with pytest.raises(ValueError):
        prepare_prize_rounds(prepared, **options)


def allocation_history(amounts, games, rounds=None):
    rounds = list(range(1, len(amounts) + 1)) if rounds is None else rounds
    numbers = pd.DataFrame({'회차': rounds, '당첨번호': [[1, 2, 3, 4, 5, 6]] * len(rounds),
                            '보너스번호': [7] * len(rounds)})
    prizes = pd.DataFrame({'회차': rounds, '1등 당첨액': pd.Series(amounts, dtype=object),
                           '1등 당첨자수': pd.Series(games, dtype=object)})
    return prepare_trend_data(numbers, prizes)


def test_equal_prize_allocation_and_total_conservation():
    from fractions import Fraction
    result = build_prize_allocation(allocation_history([12000000000], [1]))
    summary = result['summary'].set_index('번호')
    assert summary.loc[1:6, 'cumulative_numerator'].eq(12000000000).all()
    assert summary.loc[7:45, 'cumulative_numerator'].eq(0).all()
    assert summary.at[1, 'average_allocation'] == 2000000000
    assert pd.isna(summary.at[7, 'average_allocation'])
    assert Fraction(sum(summary['cumulative_numerator']), 6) == 12000000000


@pytest.mark.parametrize('basis,multiplier', [('total', 2), ('per_game', 1)])
def test_allocation_exact_large_and_nondivisible_amounts(basis, multiplier):
    from fractions import Fraction
    amount = 9007199254740993
    result = build_prize_allocation(allocation_history([str(amount), '1'], [2, 2]), basis=basis)
    summary = result['summary'].set_index('번호')
    assert summary.at[1, 'cumulative_numerator'] == (amount + 1) * multiplier
    assert isinstance(summary.at[1, 'cumulative_numerator'], int)
    assert summary.at[1, 'average_allocation'] == Fraction((amount + 1) * multiplier, 12)
    assert sum(summary['cumulative_numerator']) == 6 * (amount + 1) * multiplier


def test_excluded_and_missing_draws_keep_known_totals_and_valid_average_denominator():
    from fractions import Fraction
    prepared = allocation_history([12, None, 0, None], [1, 1, 3, 0], rounds=[1, 2, 4, 5])
    before = prepared.copy(deep=True)
    result = build_prize_allocation(prepared)
    series = result['series'].set_index(['회차', '번호'])
    assert pd.isna(series.at[(2, 1), 'allocation_numerator'])
    assert pd.isna(series.at[(3, 1), 'allocation_numerator'])
    assert series.at[(3, 1), 'cumulative_numerator'] == 12
    assert series.at[(5, 1), 'allocation_numerator'] == 0
    summary = result['summary'].set_index('번호')
    assert summary.at[1, 'appearance_count'] == 4
    assert summary.at[1, 'valid_appearance_count'] == 3
    assert summary.at[1, 'average_allocation'] == Fraction(12, 18)
    pd.testing.assert_frame_equal(prepared, before)


def test_selected_period_restarts_cumulative_amount_and_preserves_order():
    frame = allocation_history([600, 12, 24], [1, 1, 1])
    result = build_prize_allocation(frame, start=2, end=3)
    series = result['series'].set_index(['회차', '번호'])
    assert series.at[(2, 1), 'cumulative_numerator'] == 12
    assert series.at[(3, 1), 'cumulative_numerator'] == 36
    reversed_result = build_prize_allocation(frame.iloc[::-1], start=2, end=3)
    for key in ('series', 'summary'):
        pd.testing.assert_frame_equal(result[key], reversed_result[key])


def test_allocation_coverage_separates_missing_and_excluded_rounds():
    frame = allocation_history([12, None, 0, None], [1, 1, 3, 0], rounds=[1, 2, 4, 5])
    result = build_prize_allocation(frame, start=1, end=6)
    assert result['coverage'] == {
        'start_round': 1, 'end_round': 6, 'basis': 'total',
        'observed_rounds': 4, 'missing_rounds': 2,
        'valid_prize_rounds': 3, 'excluded_prize_rounds': 1, 'total_amount': 12,
    }
    details = result['rounds'].set_index('회차')
    assert details.at[2, 'exclusion_reason']
    assert details.at[3, 'exclusion_reason'] == '관측 회차 없음'
    assert details.at[5, 'amount_source'] == '당첨게임 없음'
    assert details.at[1, '당첨번호'] == [1, 2, 3, 4, 5, 6]
    assert sum(result['summary']['cumulative_numerator']) == 6 * result['coverage']['total_amount']


def test_empty_allocation_schema_and_explicit_unobserved_period():
    empty_history = prepare_trend_data(pd.DataFrame(), pd.DataFrame())
    result = build_prize_allocation(empty_history)
    populated = build_prize_allocation(allocation_history([1], [1]))
    for key in ('series', 'summary', 'rounds'):
        assert result[key].dtypes.to_dict() == populated[key].dtypes.to_dict()
    assert result['series'].empty and result['rounds'].empty
    assert len(result['summary']) == 45
    assert result['coverage']['total_amount'] == 0
    assert result['coverage']['start_round'] is None
    requested = build_prize_allocation(empty_history, start=10, end=12)
    assert requested['coverage']['missing_rounds'] == 3
    assert len(requested['series']) == 135
    assert requested['series']['allocation_numerator'].isna().all()
    assert requested['series']['cumulative_numerator'].eq(0).all()


@pytest.mark.parametrize('options', [{'start':0}, {'end':True}, {'start':1.5},
                                   {'start':3,'end':2}, {'basis':'invalid'}])
def test_invalid_allocation_bounds_and_basis(options):
    with pytest.raises(ValueError):
        build_prize_allocation(prepare_trend_data(pd.DataFrame(), pd.DataFrame()), **options)


def test_allocation_all_excluded_has_no_average_and_no_fabricated_total():
    result = build_prize_allocation(allocation_history([None], [1]))
    assert result['summary']['average_allocation'].isna().all()
    assert result['coverage']['total_amount'] == 0
    assert result['coverage']['valid_prize_rounds'] == 0
    assert result['coverage']['excluded_prize_rounds'] == 1
    assert result['series']['allocation_numerator'].isna().all()


@pytest.mark.parametrize('rank', [1, 2])
@pytest.mark.parametrize('basis', ['total', 'per_game'])
@pytest.mark.parametrize('field,value,original_reason', [
    ('당첨액', -1, '비음수 정수 필요'),
    ('당첨액', 'invalid', '숫자 형식 오류'),
    ('당첨자수', 1.5, '비음수 정수 필요'),
])
def test_original_prize_exclusion_reason_reaches_final_result(rank, basis, field, value, original_reason):
    amount_column, games_column = f'{rank}등 당첨액', f'{rank}등 당첨자수'
    field_column = f'{rank}등 {field}'
    prizes = pd.DataFrame({'회차': [101], amount_column: [100], games_column: [1]})
    prizes[field_column] = pd.Series([value], dtype=object)
    prepared = prepare_trend_data(history().loc[[20]], prizes)
    assert prepared.at[0, f'{field_column} 제외 사유'] == original_reason
    result = prepare_prize_rounds(prepared, basis=basis, rank=rank)
    assert result.at[0, 'exclusion_reason'] == f'{field_column}: {original_reason}'
    assert pd.isna(result.at[0, 'amount'])
    if rank == 1:
        details = build_prize_allocation(prepared, basis=basis)['rounds']
        assert details.at[0, 'exclusion_reason'] == f'{field_column}: {original_reason}'


def test_zero_winning_games_ignores_invalid_amount_but_preserves_prepared_reason():
    prizes = pd.DataFrame({'회차': [101], '1등 당첨액': ['invalid'], '1등 당첨자수': [0]})
    prepared = prepare_trend_data(history().loc[[20]], prizes)
    before = prepared.copy(deep=True)
    result = prepare_prize_rounds(prepared)
    assert result.at[0, 'amount'] == 0
    assert result.at[0, 'exclusion_reason'] == ''
    assert prepared.at[0, '1등 당첨액 제외 사유'] == '숫자 형식 오류'
    pd.testing.assert_frame_equal(prepared, before)


def test_prize_validation_without_saved_reason_columns_still_reports_original_error():
    raw = pd.DataFrame({'회차': [101], '1등 당첨액': ['invalid'], '1등 당첨자수': [1]})
    assert prepare_prize_rounds(raw).at[0, 'exclusion_reason'] == '1등 당첨액: 숫자 형식 오류'
