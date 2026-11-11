"""사용자 패턴 선호도 점수와 패턴 필터 조건에 따른 1세트 추출.

Scores describe historical pattern preferences, not draw probabilities.
All mutable random/history state belongs to the caller's session.
"""
from collections import Counter
from dataclasses import dataclass, asdict
from itertools import combinations, islice
import logging
import math
import numpy as np
from data_loader import normalize_draw_history
from pattern_analysis import count_number_pairs

LOG = logging.getLogger(__name__)
GROUPS = ('pair', 'sequence', 'zone', 'grid')
RELAXATIONS = ('용지 그리드 조건 완화', '구간 비율 조건 완화', '상극 쌍 기준 완화')


@dataclass(frozen=True)
class PatternConfig:
    weights: tuple = (25.0, 25.0, 25.0, 25.0)
    lookback: int = 0  # 0: all available observed draws
    recent_window: int = 20
    candidate_count: int = 1000
    top_fraction: float = 0.05
    temperature: float = 5.0
    anti_pair_quantile: float = 0.05
    grid_filter: bool = True
    zone_filter: bool = True
    pair_filter: bool = True
    max_column_count: int = 3
    max_zone_count: int = 3
    zone_target: tuple | None = None

    def validate(self):
        if len(self.weights) != 4 or any(not math.isfinite(w) or w < 0 for w in self.weights) or not math.isfinite(sum(self.weights)) or sum(self.weights) <= 0:
            raise ValueError('네 패턴 가중치는 0 이상이고 합이 0보다 커야 합니다.')
        for value, lower, upper in ((self.lookback, 0, 100000), (self.recent_window, 1, 100000),
                                    (self.candidate_count, 1, 10000), (self.max_column_count, 1, 6), (self.max_zone_count, 1, 6)):
            if not isinstance(value, int) or isinstance(value, bool) or not lower <= value <= upper:
                raise ValueError('기간·후보 수·집중 제한은 유효한 정수여야 합니다.')
        if not 0 < self.top_fraction <= 1 or not math.isfinite(self.temperature) or self.temperature <= 0:
            raise ValueError('상위 풀 비율과 온도는 양수여야 합니다.')
        if not 0 <= self.anti_pair_quantile <= 1:
            raise ValueError('상극 쌍 분위수는 0~1이어야 합니다.')
        if self.zone_target is not None and (len(self.zone_target) != 5 or sum(self.zone_target) != 6 or
                any(not isinstance(x, int) or x < 0 for x in self.zone_target)):
            raise ValueError('구간 비율은 합이 6인 다섯 개의 음이 아닌 정수여야 합니다.')


def canonical_ticket(numbers):
    values = tuple(numbers)
    if len(values) != 6 or len(set(values)) != 6 or any(
        isinstance(n, (bool, np.bool_)) or not isinstance(n, (int, np.integer)) or not 1 <= n <= 45 for n in values
    ):
        raise ValueError('번호는 1~45의 서로 다른 정수 6개여야 합니다.')
    return tuple(sorted(int(n) for n in values))


def zone_counts(numbers):
    counts = [0] * 5
    for n in numbers:
        counts[min(n // 10, 4)] += 1
    return tuple(counts)


def consecutive_count(numbers):
    return sum(b == a + 1 for a, b in zip(numbers, numbers[1:]))


class PatternPreferenceEngine:
    """Immutable historical statistics; generation never mutates global RNGs."""
    def __init__(self, history, config=None):
        self.config = config or PatternConfig()
        self.config.validate()
        history = normalize_draw_history(history)
        if self.config.lookback:
            history = history.head(self.config.lookback)
        if history.empty:
            raise ValueError('패턴 분석에 사용할 과거 회차가 없습니다.')
        self.history = history
        self.draws = [canonical_ticket(x) for x in history['당첨번호']]
        self.rounds = [int(x) for x in history['회차']]
        self.latest = set(self.draws[0])
        self.pairs = count_number_pairs(self.draws)
        self.pair_matrix = np.zeros((45, 45), dtype=int)
        for (a, b), count in self.pairs.items():
            self.pair_matrix[a-1, b-1] = self.pair_matrix[b-1, a-1] = count
        self.pair_max = max(self.pairs.values())
        all_pair_counts = [self.pairs[p] for p in combinations(range(1, 46), 2)]
        self.anti_cutoff = float(np.quantile(all_pair_counts, self.config.anti_pair_quantile))
        self.anti_pairs = {p for p in combinations(range(1, 46), 2)
                           if self.pairs[p] == 0 or self.pairs[p] < self.anti_cutoff}
        recent = self.draws[:self.config.recent_window]
        self.sequence_hist = Counter(consecutive_count(x) for x in recent)
        self.zone_hist = Counter(zone_counts(x) for x in recent)
        self.carry_hist = Counter(len(set(self.draws[i]) & set(self.draws[i+1]))
                                  for i in range(min(self.config.recent_window, len(self.draws)-1))
                                  if self.rounds[i] - self.rounds[i+1] == 1)
        self.cycles = {}
        for n in range(1, 46):
            appearances = [r for r, row in zip(self.rounds, self.draws) if n in row]
            intervals = [a-b for a, b in zip(appearances, appearances[1:])]
            self.cycles[n] = (self.rounds[0]-appearances[0] if appearances else None,
                              float(np.mean(intervals)) if intervals else None)
        # Number preference weights are sampling weights, not inclusion probabilities.
        frequency = Counter(n for row in self.draws for n in row)
        recent_freq = Counter(n for row in recent for n in row)
        weights = np.array([1 + frequency[n]/len(self.draws) + recent_freq[n]/len(recent)
                            for n in range(1, 46)], dtype=float)
        self.number_weights = weights / weights.sum()

    def score(self, numbers):
        numbers = canonical_ticket(numbers)
        pairs = list(combinations(numbers, 2))
        pair_score = 100 * sum(self.pairs[p] for p in pairs) / (15 * self.pair_max)
        anti = [p for p in pairs if p in self.anti_pairs]
        consecutive = consecutive_count(numbers)
        carry = len(set(numbers) & self.latest)
        sequence_parts = [self.sequence_hist[consecutive] / max(self.sequence_hist.values())]
        if self.carry_hist:
            sequence_parts.append(self.carry_hist[carry] / max(self.carry_hist.values()))
        cycle_fit = [math.exp(-abs((absence+1)-interval)/interval)
                     for n in numbers for absence, interval in [self.cycles[n]]
                     if absence is not None and interval is not None and interval > 0]
        if cycle_fit:
            sequence_parts.append(float(np.mean(cycle_fit)))
        sequence_score = 100 * float(np.mean(sequence_parts))
        zones = zone_counts(numbers)
        target = self.config.zone_target
        zone_score = (100 * (1 - sum(abs(a-b) for a, b in zip(zones, target))/12)
                      if target else 100 * self.zone_hist[zones] / max(self.zone_hist.values()))
        coords = [((n-1)//7, (n-1)%7) for n in numbers]
        columns = Counter(c for _, c in coords)
        rows = [r for r, _ in coords]
        cols = [c for _, c in coords]
        row_span, col_span = max(rows)-min(rows), max(cols)-min(cols)
        corner_cluster = ((max(rows) <= 2 or min(rows) >= 4) and
                          (max(cols) <= 2 or min(cols) >= 4))
        grid_score = 100 * ((row_span/6 + col_span/6 + (6-max(columns.values()))/5)/3)
        scores = dict(zip(GROUPS, (pair_score, sequence_score, zone_score, grid_score)))
        contributions = {name: scores[name]*w/sum(self.config.weights)
                         for name, w in zip(GROUPS, self.config.weights)}
        violations = {
            'grid': self.config.grid_filter and (max(columns.values()) > self.config.max_column_count or corner_cluster),
            'zone': self.config.zone_filter and (max(zones) > self.config.max_zone_count or (target is not None and zones != target)),
            'pair': self.config.pair_filter and bool(anti),
        }
        return {'numbers': numbers, 'score': sum(contributions.values()), 'groups': scores,
                'contributions': contributions, 'violations': violations,
                'features': {'anti_pairs': anti, 'pair_count_sum': sum(self.pairs[p] for p in pairs),
                             'consecutive_pairs': consecutive, 'carry_over_count': carry,
                             'zones': zones, 'max_column_count': max(columns.values()),
                             'corner_cluster': corner_cluster, 'cycle_fit': cycle_fit}}

    def _candidates(self, seen, rng):
        result = set()
        for _ in range(self.config.candidate_count * 10):
            row = tuple(sorted(int(x) for x in rng.choice(np.arange(1, 46), size=6, replace=False, p=self.number_weights)))
            if row not in seen:
                result.add(row)
            if len(result) == self.config.candidate_count:
                break
        if not result:
            # Finite exhaustive unused-ticket fallback; these are still fully scored.
            result.update(islice((row for row in combinations(range(1, 46), 6) if row not in seen), self.config.candidate_count))
        return sorted(result)

    def draw(self, seen=(), rng=None, candidates=None):
        """Return one unseen set; relaxed paths take the highest preference score.

        candidates permits deterministic candidate sets for evaluation and tests.
        None samples a fresh pool. No filter stage relaxes validity or deduplication.
        """
        rng = rng if rng is not None else np.random.default_rng()
        seen = {canonical_ticket(row) for row in seen}
        if len(seen) == math.comb(45, 6):
            raise ValueError('모든 조합을 이미 추출했습니다. 이력을 초기화해 주세요.')
        rows = self._candidates(seen, rng) if candidates is None else sorted({canonical_ticket(x) for x in candidates} - seen)
        if not rows:
            raise ValueError('이번 후보에 미추출 조합이 없습니다.')
        scored = [self.score(row) for row in rows]
        audits = []
        for stage in range(4):
            relaxed_keys = set(('grid', 'zone', 'pair')[:stage])
            eligible = [row for row in scored if not any(value and key not in relaxed_keys
                                                        for key, value in row['violations'].items())]
            audits.append({'stage': stage, 'eligible': len(eligible), 'evaluated': len(rows),
                           'violations': {key: sum(bool(x['violations'][key]) for x in scored) for key in ('grid', 'zone', 'pair')}})
            if not eligible:
                continue
            eligible.sort(key=lambda x: (-x['score'], x['numbers']))
            if stage:
                pool = [row for row in eligible if math.isclose(row['score'], eligible[0]['score'], abs_tol=1e-12, rel_tol=0)]
            else:
                cutoff = eligible[max(0, math.ceil(len(eligible)*self.config.top_fraction)-1)]['score']
                pool = [row for row in eligible if row['score'] >= cutoff]
            logits = np.array([x['score'] for x in pool])
            probabilities = np.exp((logits-logits.max())/self.config.temperature)
            probabilities /= probabilities.sum()
            selected = dict(pool[int(rng.choice(len(pool), p=probabilities))])
            enabled_filters = (self.config.grid_filter, self.config.zone_filter, self.config.pair_filter)
            selected.update({'relaxations': [label for label, enabled in zip(RELAXATIONS[:stage], enabled_filters) if enabled], 'stage': stage,
                             'audits': audits, 'pool_size': len(pool), 'candidate_count': len(rows),
                             'eligible_count': len(eligible), 'config': asdict(self.config),
                             'data_range': [self.rounds[-1], self.rounds[0]], 'draw_count': len(self.draws),
                             'missing_rounds': self.rounds[0]-self.rounds[-1]+1-len(self.rounds)})
            if stage:
                LOG.info('패턴 필터 조건 완화: %s', ' → '.join(selected['relaxations']))
            return selected
        raise RuntimeError('필터 완화 후 후보 선택에 실패했습니다.')
