from dataclasses import replace
from pathlib import Path
import random
import numpy as np
import pandas as pd
import pytest
from pattern_preference import PatternConfig, PatternPreferenceEngine, canonical_ticket, zone_counts
from data_loader import LottoDataLoader
from recommendation_system import LottoRecommendationSystem


@pytest.fixture(scope='module')
def history():
    loader = LottoDataLoader(Path(__file__).resolve().parents[1] / 'Data/645_251227.csv')
    loader.load_data(); loader.preprocess(); loader.extract_numbers()
    return loader.numbers_df


def test_patterns_have_real_features_and_weighted_effects():
    frame = pd.DataFrame({'회차': [13, 12, 11], '당첨번호': [
        [1, 2, 10, 20, 30, 40], [1, 2, 11, 21, 31, 41], [1, 3, 12, 22, 32, 42]]})
    e = PatternPreferenceEngine(frame)
    row = e.score([1, 2, 10, 20, 30, 40])
    assert e.pairs[(1, 2)] == 2
    assert np.array_equal(e.pair_matrix, e.pair_matrix.T)
    assert np.trace(e.pair_matrix) == 0
    assert e.pair_matrix.sum() == 3*15*2
    assert row['features']['consecutive_pairs'] == 1
    assert row['features']['carry_over_count'] == 6
    assert row['features']['zones'] == (2, 1, 1, 1, 1)
    assert zone_counts([9, 10, 19, 20, 39, 45]) == (1, 2, 1, 1, 1)
    assert e.cycles[2] == (0, 1.0)
    for group, i in zip(('pair', 'sequence', 'zone', 'grid'), range(4)):
        weights = tuple(1 if j == i else 0 for j in range(4))
        scorer = PatternPreferenceEngine(frame, PatternConfig(weights=weights))
        assert scorer.score(row['numbers'])['score'] == pytest.approx(row['groups'][group])
    assert e.score([1, 8, 15, 22, 29, 36])['violations']['grid']
    assert e.score([1, 2, 3, 4, 10, 20])['violations']['zone']
    assert e.score([4, 5, 6, 7, 8, 9])['violations']['pair']


@pytest.mark.parametrize('stage', [0, 1, 2, 3])
def test_relaxation_order_and_best_remaining_score(stage):
    # All pairs of this observed ticket are known. Configure violations separately.
    ticket = (1, 8, 15, 22, 29, 36)
    history_ticket = ticket if stage < 3 else (2, 9, 16, 23, 30, 37)
    frame = pd.DataFrame({'회차': [1], '당첨번호': [history_ticket]})
    config = PatternConfig(grid_filter=stage >= 1, zone_target=(6, 0, 0, 0, 0) if stage >= 2 else None)
    e = PatternPreferenceEngine(frame, config)
    result = e.draw(rng=np.random.default_rng(1), candidates=[ticket])
    assert result['stage'] == stage
    assert len(result['relaxations']) == stage
    assert [a['stage'] for a in result['audits']] == list(range(stage+1))
    assert all(a['eligible'] == 0 for a in result['audits'][:-1])
    assert result['numbers'] == ticket


def test_relaxation_returns_best_scored_not_random(history):
    config = PatternConfig(zone_target=(6, 0, 0, 0, 0), grid_filter=False, pair_filter=False)
    e = PatternPreferenceEngine(history, config)
    candidates = [(1, 8, 15, 22, 29, 36), (2, 10, 20, 30, 40, 45)]
    expected = max(e.score(x)['score'] for x in candidates)
    for seed in range(10):
        out = e.draw(candidates=candidates, rng=np.random.default_rng(seed))
        assert out['stage'] == 2
        assert out['score'] == expected
        assert out['groups']['grid'] > 0


def test_one_hundred_draws_are_unique_and_dont_change_global_random(history):
    e = PatternPreferenceEngine(history)
    python_state, numpy_state = random.getstate(), np.random.get_state()
    seen = set(); rng = np.random.default_rng(872)
    for _ in range(100):
        result = e.draw(seen=seen, rng=rng)
        assert canonical_ticket(result['numbers']) not in seen
        assert 0 <= result['score'] <= 100
        seen.add(result['numbers'])
    assert len(seen) == 100
    assert random.getstate() == python_state
    assert all(np.array_equal(a, b) for a, b in zip(np.random.get_state(), numpy_state))


def test_softmax_upper_pool_reproducible_and_diverse(history):
    config = PatternConfig(grid_filter=False, zone_filter=False, pair_filter=False, top_fraction=.5, temperature=10)
    e = PatternPreferenceEngine(history, config)
    pool = e._candidates(set(), np.random.default_rng(7))[:50]
    scores = sorted((e.score(x)['score'] for x in pool), reverse=True)
    first = e.draw(candidates=pool, rng=np.random.default_rng(41))
    assert first == e.draw(candidates=pool, rng=np.random.default_rng(41))
    outputs = [e.draw(candidates=pool, rng=np.random.default_rng(seed)) for seed in range(40)]
    assert all(row['score'] >= scores[24] for row in outputs)
    assert len({row['numbers'] for row in outputs}) > 1
    seen = {first['numbers']}
    assert e.draw(seen=seen, candidates=pool, rng=np.random.default_rng(41))['numbers'] not in seen


def test_filter_changes_do_not_relax_seen_and_all_zero_weights_rejected(history):
    ticket = (1, 2, 3, 4, 5, 6)
    e = PatternPreferenceEngine(history)
    with pytest.raises(ValueError, match='미추출'):
        e.draw(seen=[ticket], candidates=[tuple(reversed(ticket))])
    with pytest.raises(ValueError, match='가중치'):
        PatternPreferenceEngine(history, PatternConfig(weights=(0, 0, 0, 0)))
    with pytest.raises(ValueError, match='번호'):
        e.draw(candidates=[(1, 2, 3, 4, 5, 46)])


def test_candidate_exhaustion_uses_scored_unseen_fallback(history):
    e = PatternPreferenceEngine(history, PatternConfig(candidate_count=3))
    class RepeatingRng:
        def choice(self, *args, **kwargs): return np.array([1, 2, 3, 4, 5, 6])
    rows = e._candidates({(1, 2, 3, 4, 5, 6)}, RepeatingRng())
    assert len(rows) == 3
    assert (1, 2, 3, 4, 5, 6) not in rows
    assert all(np.isfinite(e.score(row)['score']) for row in rows)


def test_carry_ignores_missing_rounds_and_input_order(history):
    subset = history.iloc[[0, 3, 7]].copy()
    e = PatternPreferenceEngine(subset)
    assert not e.carry_hist
    shuffled = PatternPreferenceEngine(subset.iloc[::-1].set_axis([900, 700, -50]))
    ticket = [1, 11, 21, 31, 41, 45]
    assert e.score(ticket) == shuffled.score(ticket)


def test_legacy_random_is_local_and_seeded():
    recommender = LottoRecommendationSystem.__new__(LottoRecommendationSystem)
    state = random.getstate(); np_state = np.random.get_state()
    a = recommender.generate_random(5, seed=42)
    assert a == recommender.generate_random(5, seed=42)
    assert state == random.getstate()
    assert all(np.array_equal(x, y) for x, y in zip(np_state, np.random.get_state()))


@pytest.fixture(scope='module')
def legacy_recommender(history):
    from types import SimpleNamespace
    from prediction_model import LottoPredictionModel
    loader = SimpleNamespace(df=history, numbers_df=history)
    model = LottoPredictionModel(loader)
    model.train_all_patterns()
    return LottoRecommendationSystem(model)


@pytest.mark.parametrize('method', ['generate_by_score', 'generate_by_probability', 'generate_by_pattern',
    'generate_grid_based', 'generate_image_based', 'generate_with_consecutive',
    'generate_hybrid', 'generate_safe_strategy', 'generate_ensemble'])
def test_legacy_strategies_remain_seed_reproducible_and_rng_isolated(legacy_recommender, method):
    py_state, np_state = random.getstate(), np.random.get_state()
    generate = getattr(legacy_recommender, method)
    a = generate(n_combinations=1, seed=47)
    b = generate(n_combinations=1, seed=47)
    assert a == b
    assert a and all(len(canonical_ticket(row)) == 6 for row in a)
    assert py_state == random.getstate()
    assert all(np.array_equal(x, y) for x, y in zip(np_state, np.random.get_state()))
