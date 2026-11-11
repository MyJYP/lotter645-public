from pathlib import Path
from types import SimpleNamespace
import pandas as pd
import pytest
from data_loader import LottoDataLoader, normalize_draw_history
from prediction_model import LottoPredictionModel


def model_for(frame):
    return LottoPredictionModel(SimpleNamespace(df=frame, numbers_df=frame))


def test_features_ignore_order_and_labels_and_use_round_gaps():
    frame = pd.DataFrame({'회차': [90, 100, 97], '당첨번호': [
        [1, 2, 3, 4, 5, 6], [1, 7, 8, 9, 10, 11], [1, 2, 12, 13, 14, 15]]}, index=[900, -2, 57])
    a = model_for(frame).extract_number_features()
    b = model_for(frame.iloc[::-1].reset_index(drop=True)).extract_number_features()
    assert a == b
    assert a[1]['absence_length'] == 0
    assert a[1]['avg_interval'] == 5  # intervals 100-97 and 97-90
    assert a[2]['absence_length'] == 3
    assert a[2]['avg_interval'] == 7
    assert a[45]['absence_length'] == 11
    assert a[45]['absence_is_observation_bound']
    assert a[7]['appearance_count'] == 1
    assert a[7]['avg_interval'] == 0
    assert all(x['avg_interval'] >= 0 for x in a.values())


def test_actual_csv_loader_and_cutoff():
    path = Path(__file__).resolve().parents[1] / 'Data/645_251227.csv'
    loader = LottoDataLoader(path).load_data_until_round(999)
    assert loader.numbers_df['회차'].max() == 999
    features = LottoPredictionModel(loader).extract_number_features()
    for number in loader.get_round_data(999):
        assert features[number]['absence_length'] == 0
    assert all(x['avg_interval'] > 0 for x in features.values())
    assert list(loader.numbers_df.index) == list(range(len(loader.numbers_df)))


def test_empty_and_duplicate_rounds_are_explicit():
    empty = pd.DataFrame(columns=['회차', '당첨번호'])
    with pytest.raises(ValueError, match='과거 회차'):
        model_for(empty).extract_number_features()
    with pytest.raises(ValueError, match='중복 회차'):
        normalize_draw_history(pd.DataFrame({'회차': [1, 1]}))
