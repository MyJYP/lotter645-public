"""
로또 645 번호 추천 시스템
다양한 전략으로 번호 조합 생성
"""
import numpy as np
import random
from collections import Counter
from itertools import combinations


class LottoRecommendationSystem:
    """로또 번호 추천 시스템"""

    def __init__(self, prediction_model):
        """
        Args:
            prediction_model: LottoPredictionModel 인스턴스
        """
        self.model = prediction_model
        self.loader = prediction_model.loader

        # 그리드 패턴 데이터 초기화 (7x7 그리드)
        self._init_grid_pattern_data()

        # Phase 3: 제외수 필터링 데이터 초기화
        self._init_phase3_filters()

        # 이미지 패턴 분석기 초기화
        from image_pattern_analysis import ImagePatternAnalysis
        self.image_analyzer = ImagePatternAnalysis(self.loader)

        # 패턴 분석기 초기화 (신규 피처 통합)
        from pattern_analysis import PatternAnalysis
        self.pattern_analyzer = PatternAnalysis(self.loader)

        # 분석 데이터 로드 (스코어링 속도를 위해 미리 계산)
        self.pair_counts, self.never_appeared = self.pattern_analyzer.analyze_compatibility()
        self.never_appeared_set = set(self.never_appeared)

        self.prime_df = self.pattern_analyzer.analyze_prime_composite()
        self.prime_score_map = dict(zip(self.prime_df['소수개수'], self.prime_df['비율(%)']))
        self.primes = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43}

    def _init_grid_pattern_data(self):
        """그리드 패턴 관련 데이터 초기화"""
        # 번호를 그리드 좌표로 매핑 (1-45)
        self.number_to_position = {}
        number = 1
        for row in range(7):
            for col in range(7):
                if number <= 45:
                    self.number_to_position[number] = (row, col)
                    number += 1

        # 그리드 구역별 번호 정의
        self.grid_zones = {
            'corner': [1, 7, 43, 45],  # 모서리 (4칸)
            'middle': [16, 17, 18, 19, 20, 23, 24, 25, 26, 27, 31, 32, 33, 34],  # 중간 (12칸)
            'center': [24, 25, 26, 31, 32, 33, 38, 39, 40],  # 중앙부 (9칸)
            'anti_diagonal': [7, 13, 19, 25, 31, 37, 43]  # 반대 대각선
        }

        # 그리드 가중치 (1칸당 평균 출현 기준)
        self.grid_weights = {
            'middle': 1.46,    # 108.3 / 74.0 = 1.46
            'center': 1.09,    # 80.7 / 74.0 = 1.09
            'edge': 0.91,      # 67.7 / 74.0 = 0.91
            'corner': 0.83     # 61.5 / 74.0 = 0.83
        }

    def _init_phase3_filters(self):
        """Phase 3: 제외수 필터링을 위한 데이터 초기화"""
        # 1. 과열 번호 (최근 10회차 중 4회 이상 출현)
        recent_10 = self.model.numbers_df.head(10)
        recent_nums = []
        for _, row in recent_10.iterrows():
            recent_nums.extend(row['당첨번호'])

        counts = Counter(recent_nums)
        self.overheated_numbers = {num for num, count in counts.items() if count >= 4}

    def _get_grid_zone(self, number):
        """번호가 속한 그리드 구역 반환"""
        if number in self.grid_zones['corner']:
            return 'corner'
        elif number in self.grid_zones['middle']:
            return 'middle'
        elif number in self.grid_zones['center']:
            return 'center'
        else:
            return 'edge'

    def _calculate_grid_score(self, numbers):
        """그리드 패턴 기반 점수 계산"""
        score = 0

        # 1. 위치 기반 가중치
        for num in numbers:
            zone = self._get_grid_zone(num)
            weight = self.grid_weights.get(zone, 1.0)
            score += weight * 10  # 기본 10점에 가중치 적용

        # 2. 중간 영역 보너스 (3-4개 권장)
        middle_count = sum(1 for n in numbers if n in self.grid_zones['middle'])
        if 3 <= middle_count <= 4:
            score += 20

        # 3. 반대 대각선 보너스 (1-2개 권장)
        anti_diag_count = sum(1 for n in numbers if n in self.grid_zones['anti_diagonal'])
        if 1 <= anti_diag_count <= 2:
            score += 15

        # 4. 모서리 페널티 (2개 이상이면 감점)
        corner_count = sum(1 for n in numbers if n in self.grid_zones['corner'])
        if corner_count >= 2:
            score -= 15

        # 5. 공간적 군집도 (평균 거리 4.0~5.5 권장)
        avg_distance = self._calculate_spatial_distance(numbers)
        if 4.0 <= avg_distance <= 5.5:
            score += 20
        elif avg_distance < 3.0 or avg_distance > 6.0:
            score -= 10  # 너무 밀집/분산되면 감점

        return score

    def _calculate_spatial_distance(self, numbers):
        """번호들 간의 평균 맨해튼 거리 계산"""
        distances = []
        nums = sorted(numbers)

        for i in range(len(nums)):
            for j in range(i+1, len(nums)):
                pos1 = self.number_to_position.get(nums[i])
                pos2 = self.number_to_position.get(nums[j])

                if pos1 and pos2:
                    # 맨해튼 거리
                    dist = abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
                    distances.append(dist)

        return np.mean(distances) if distances else 0

    def _is_valid_combination(self, numbers, strict=False):
        """번호 조합이 유효한지 검증"""
        nums = sorted(numbers)

        # 1. 개수 확인
        if len(nums) != 6:
            return False

        # 2. 범위 확인
        if any(n < 1 or n > 45 for n in nums):
            return False

        # 3. 중복 확인
        if len(set(nums)) != 6:
            return False

        if not strict:
            return True

        # 엄격한 검증: 패턴 기반

        # 4. 구간 분포 확인 (한 구간에 5개 이상 X)
        low = sum(1 for n in nums if 1 <= n <= 15)
        mid = sum(1 for n in nums if 16 <= n <= 30)
        high = sum(1 for n in nums if 31 <= n <= 45)

        if max(low, mid, high) > 4:
            return False

        # 5. 홀짝 비율 확인 (0:6 또는 6:0 제외)
        odd = sum(1 for n in nums if n % 2 == 1)
        if odd == 0 or odd == 6:
            return False

        # 6. 연속 번호 체크 (4개 이상 연속 제외 - 극히 드뭄)
        consecutive_count = 0
        for i in range(len(nums)-1):
            if nums[i+1] == nums[i] + 1:
                consecutive_count += 1
                if consecutive_count >= 3:  # 4개 연속
                    return False
            else:
                consecutive_count = 0

        return True

    def _calculate_combination_score(self, numbers):
        """조합에 대한 점수 계산"""
        score = 0

        # 1. 개별 번호 점수 합
        for num in numbers:
            score += self.model.number_scores[num]['total_score']

        # 2. 패턴 보너스

        # 연속 번호 있으면 보너스 (56% 확률이므로)
        nums = sorted(numbers)
        has_consecutive = False
        for i in range(len(nums)-1):
            if nums[i+1] == nums[i] + 1:
                has_consecutive = True
                score += 10
                break

        # 구간 분포 보너스
        low = sum(1 for n in nums if 1 <= n <= 15)
        mid = sum(1 for n in nums if 16 <= n <= 30)
        high = sum(1 for n in nums if 31 <= n <= 45)

        # 균형잡힌 분포
        if 1 <= low <= 3 and 1 <= mid <= 3 and 1 <= high <= 3:
            score += 15

        # 홀짝 균형
        odd = sum(1 for n in nums if n % 2 == 1)
        if 2 <= odd <= 4:
            score += 10

        # 합계 범위
        total = sum(nums)
        mean = self.model.patterns['sum']['mean']
        std = self.model.patterns['sum']['std']

        if mean - std <= total <= mean + std:
            score += 10

        # 3. 그리드 패턴 보너스 (NEW)
        grid_score = self._calculate_grid_score(numbers)
        score += grid_score * 0.5  # 가중치 적용 (50%)

        # 4. 이미지 패턴 보너스 (NEW)
        image_score_data = self.image_analyzer.calculate_image_score(numbers)
        score += image_score_data['total_score'] * 0.3  # 가중치 적용 (30%)

        # 5. 궁합수/상극수 보너스 (NEW)
        # 조합 내의 모든 2개 쌍 확인
        pairs = list(combinations(sorted(numbers), 2))
        for pair in pairs:
            # 상극수 페널티 (한 번도 같이 안 나온 쌍)
            if pair in self.never_appeared_set:
                score -= 10  # 페널티 완화 (-20 -> -10)

            # 궁합수 보너스 (자주 같이 나온 쌍)
            count = self.pair_counts.get(pair, 0)
            if count >= 5:  # 5회 이상 같이 나온 경우
                score += count * 0.5  # 보너스 강화 (0.2 -> 0.5)

        # 6. 소수/합성수 패턴 보너스 (NEW)
        prime_count = sum(1 for n in numbers if n in self.primes)
        # 해당 소수 개수의 출현 확률(%)을 점수에 반영 (예: 소수 2개는 30% 확률 -> +15점)
        prime_prob = self.prime_score_map.get(prime_count, 0)
        score += prime_prob * 0.5

        return score

    def _check_phase3_constraints(self, combination):
        """Phase 3: 강력한 제외수 필터링 적용 (고정 모드용)"""
        # 1. 과열 번호 필터링 (Kill Number)
        # 과열 번호가 포함되어 있으면 제외 (회귀 법칙: 너무 뜨거운 번호는 식을 가능성 높음)
        for num in combination:
            if num in self.overheated_numbers:
                return False

        # 2. 상극수 포함 여부 (절대 제외)
        # 조합 내의 모든 쌍을 확인하여 역사적으로 한 번도 같이 안 나온 쌍이 있으면 제외
        pairs = list(combinations(sorted(combination), 2))
        for pair in pairs:
            if pair in self.never_appeared_set:
                return False

        # 3. 희박 패턴 제외 (4연속 번호)
        sorted_nums = sorted(combination)
        consecutive_count = 0
        for i in range(len(sorted_nums)-1):
            if sorted_nums[i+1] == sorted_nums[i] + 1:
                consecutive_count += 1
                if consecutive_count >= 3: # 4개 연속 (차이가 1인 횟수가 3번)
                    return False
            else:
                consecutive_count = 0

        return True

    def _find_best_combination(self, candidates, n_combinations=1, constraint_func=None, custom_score_func=None, apply_phase3=False):
        """최적 조합 탐색 (완전 탐색) - Phase 1 결정론적 엔진"""
        # 후보군이 너무 많으면 조합이 폭발하므로 제한 (22C6 = 74,613, 23C6 = 100,947)
        limit = 22
        if len(candidates) > limit:
            candidates = candidates[:limit]

        all_combos = list(combinations(candidates, 6))
        valid_combos = []

        for combo in all_combos:
            # 제약 조건 확인
            if constraint_func and not constraint_func(combo):
                continue

            # Phase 3 필터링 (옵션)
            if apply_phase3 and not self._check_phase3_constraints(combo):
                continue

            # 유효성 검사 (기본)
            if not self._is_valid_combination(combo):
                continue

            # 점수 계산
            if custom_score_func:
                score = custom_score_func(combo)
            else:
                score = self._calculate_combination_score(combo)

            valid_combos.append((combo, score))

        # 점수순 정렬
        valid_combos.sort(key=lambda x: x[1], reverse=True)

        # 상위 n개 반환
        return [list(c[0]) for c in valid_combos[:n_combinations]]

    def generate_by_score(self, n_combinations=5, use_top=20, seed=None, best_only=False):
        """점수 기반 추천"""
        py_rng = random.Random(seed)
        print(f"\n🎯 점수 기반 추천 (상위 {use_top}개 번호 활용)")

        if best_only:
            print("  ✨ 최적 조합 모드 (랜덤 제외)")
            # 상위 번호들로 만들 수 있는 모든 조합 중 최고 점수 조합 반환
            top_candidates = self.model.get_top_numbers(max(use_top, 22))
            return self._find_best_combination(top_candidates, n_combinations, apply_phase3=True)

        top_numbers = self.model.get_top_numbers(use_top)
        combinations_list = []

        # 상위 번호들로 가능한 조합 생성
        max_attempts = 10000
        attempts = 0

        while len(combinations_list) < n_combinations and attempts < max_attempts:
            # 상위 번호에서 가중치 샘플링
            selected = py_rng.sample(top_numbers, 6)

            if self._is_valid_combination(selected):
                sorted_selected = tuple(sorted(selected))
                if sorted_selected not in combinations_list:
                    combinations_list.append(sorted_selected)

            attempts += 1

        # 점수 순으로 정렬
        scored_combos = []
        for combo in combinations_list:
            score = self._calculate_combination_score(combo)
            scored_combos.append((combo, score))

        scored_combos.sort(key=lambda x: x[1], reverse=True)

        results = [list(combo) for combo, _ in scored_combos[:n_combinations]]

        for i, (combo, score) in enumerate(scored_combos[:n_combinations], 1):
            print(f"  {i}. {list(combo)} (점수: {score:.1f})")

        return results

    def generate_by_probability(self, n_combinations=5, seed=None, best_only=False):
        """선호 가중치 기반 추천"""
        np_rng = np.random.default_rng(seed)
        print(f"\n🎲 선호 가중치 기반 추천")

        if best_only:
            print("  ✨ 최적 조합 모드 (랜덤 제외)")
            # 확률 가중치가 높은 상위 번호들을 후보로 선정
            weights = self.model.get_probability_weights()
            sorted_nums = sorted(range(1, 46), key=lambda x: weights[x], reverse=True)
            top_candidates = sorted_nums[:22]
            return self._find_best_combination(top_candidates, n_combinations, apply_phase3=True)

        weights = self.model.get_probability_weights()
        numbers = list(range(1, 46))
        probabilities = [weights[n] for n in numbers]

        combinations_list = []
        max_attempts = 10000
        attempts = 0

        while len(combinations_list) < n_combinations and attempts < max_attempts:
            # 가중치 기반 샘플링
            selected = np_rng.choice(numbers, size=6, replace=False, p=probabilities)

            if self._is_valid_combination(selected):
                sorted_selected = tuple(sorted(selected))
                if sorted_selected not in combinations_list:
                    combinations_list.append(sorted_selected)

            attempts += 1

        results = [list(combo) for combo in combinations_list[:n_combinations]]

        for i, combo in enumerate(results, 1):
            print(f"  {i}. {combo}")

        return results

    def generate_by_pattern(self, n_combinations=5, seed=None, best_only=False):
        """패턴 기반 추천 (연속, 구간, 홀짝 고려)"""
        py_rng = random.Random(seed)
        print(f"\n🔄 패턴 기반 추천")

        # 가장 흔한 패턴 가져오기
        section_pattern = self.model.patterns['section']['most_common'][0][0]  # (저, 중, 고)
        odd_even_pattern = self.model.patterns['odd_even']['most_common'][0][0]  # (홀, 짝)

        if best_only:
            print("  ✨ 최적 조합 모드 (랜덤 제외)")
            # 상위 번호 중 패턴을 만족하는 최적 조합 탐색
            top_candidates = self.model.get_top_numbers(25)

            def pattern_constraint(combo):
                low = sum(1 for n in combo if 1 <= n <= 15)
                mid = sum(1 for n in combo if 16 <= n <= 30)
                high = sum(1 for n in combo if 31 <= n <= 45)
                odd = sum(1 for n in combo if n % 2 == 1)
                return (low, mid, high) == section_pattern and abs(odd - odd_even_pattern[0]) <= 1

            return self._find_best_combination(top_candidates, n_combinations, constraint_func=pattern_constraint, apply_phase3=True)

        print(f"  목표 구간 분포: 저{section_pattern[0]}/중{section_pattern[1]}/고{section_pattern[2]}")
        print(f"  목표 홀짝 분포: 홀{odd_even_pattern[0]}/짝{odd_even_pattern[1]}")

        combinations_list = []
        max_attempts = 10000
        attempts = 0

        top_numbers = self.model.get_top_numbers(30)  # 상위 30개에서 선택

        while len(combinations_list) < n_combinations and attempts < max_attempts:
            selected = []

            # 구간별로 번호 선택
            low_pool = [n for n in top_numbers if 1 <= n <= 15]
            mid_pool = [n for n in top_numbers if 16 <= n <= 30]
            high_pool = [n for n in top_numbers if 31 <= n <= 45]

            # 구간 패턴 맞추기
            if len(low_pool) >= section_pattern[0]:
                selected.extend(py_rng.sample(low_pool, section_pattern[0]))
            if len(mid_pool) >= section_pattern[1]:
                selected.extend(py_rng.sample(mid_pool, section_pattern[1]))
            if len(high_pool) >= section_pattern[2]:
                selected.extend(py_rng.sample(high_pool, section_pattern[2]))

            # 부족하면 나머지 채우기
            while len(selected) < 6:
                remaining = [n for n in top_numbers if n not in selected]
                if remaining:
                    selected.append(py_rng.choice(remaining))
                else:
                    break

            if len(selected) == 6 and self._is_valid_combination(selected):
                # 홀짝 패턴도 확인
                odd_count = sum(1 for n in selected if n % 2 == 1)
                if abs(odd_count - odd_even_pattern[0]) <= 1:  # 오차 1 허용
                    sorted_selected = tuple(sorted(selected))
                    if sorted_selected not in combinations_list:
                        combinations_list.append(sorted_selected)

            attempts += 1

        results = [list(combo) for combo in combinations_list[:n_combinations]]

        for i, combo in enumerate(results, 1):
            odd = sum(1 for n in combo if n % 2 == 1)
            low = sum(1 for n in combo if 1 <= n <= 15)
            mid = sum(1 for n in combo if 16 <= n <= 30)
            high = sum(1 for n in combo if 31 <= n <= 45)
            print(f"  {i}. {combo} [홀{odd}/짝{6-odd}, 저{low}/중{mid}/고{high}]")

        return results

    def generate_grid_based(self, n_combinations=5, seed=None, best_only=False):
        """그리드 패턴 기반 추천 (NEW)"""
        py_rng = random.Random(seed)
        print(f"\n🎨 그리드 패턴 기반 추천")

        if best_only:
            print("  ✨ 최적 조합 모드 (랜덤 제외)")
            top_candidates = self.model.get_top_numbers(25)

            def grid_score_func(combo):
                # 그리드 점수 + 기본 점수
                return self._calculate_grid_score(combo) + self._calculate_combination_score(combo) * 0.5

            return self._find_best_combination(top_candidates, n_combinations, custom_score_func=grid_score_func, apply_phase3=True)

        # 중간 영역 번호 우선 선택
        middle_numbers = self.grid_zones['middle']
        anti_diag_numbers = self.grid_zones['anti_diagonal']
        top_numbers = self.model.get_top_numbers(45)

        combinations_list = []
        max_attempts = 10000
        attempts = 0

        while len(combinations_list) < n_combinations and attempts < max_attempts:
            selected = []

            # 1. 중간 영역에서 3-4개 선택
            middle_pool = [n for n in middle_numbers if n in top_numbers[:30]]
            if len(middle_pool) >= 3:
                num_middle = py_rng.choice([3, 4])
                selected.extend(py_rng.sample(middle_pool, min(num_middle, len(middle_pool))))

            # 2. 반대 대각선에서 1-2개 선택
            anti_diag_pool = [n for n in anti_diag_numbers if n not in selected and n in top_numbers[:30]]
            if len(anti_diag_pool) >= 1:
                num_anti_diag = py_rng.choice([1, 2])
                selected.extend(py_rng.sample(anti_diag_pool, min(num_anti_diag, len(anti_diag_pool))))

            # 3. 나머지는 상위 번호에서 선택 (모서리 제외)
            remaining_pool = [n for n in top_numbers[:30]
                            if n not in selected and n not in self.grid_zones['corner']]

            while len(selected) < 6 and remaining_pool:
                selected.append(py_rng.choice(remaining_pool))
                remaining_pool = [n for n in remaining_pool if n not in selected]

            if len(selected) == 6:
                # 평균 거리 검증 (4.0~5.5 권장)
                avg_distance = self._calculate_spatial_distance(selected)

                if 3.5 <= avg_distance <= 6.0:  # 약간 여유 있게
                    if self._is_valid_combination(selected):
                        sorted_selected = tuple(sorted(selected))
                        if sorted_selected not in combinations_list:
                            combinations_list.append(sorted_selected)

            attempts += 1

        # 그리드 점수로 정렬
        scored_combos = []
        for combo in combinations_list:
            grid_score = self._calculate_grid_score(combo)
            total_score = self._calculate_combination_score(combo)
            scored_combos.append((combo, grid_score, total_score))

        scored_combos.sort(key=lambda x: x[2], reverse=True)  # 총점으로 정렬

        results = [list(combo) for combo, _, _ in scored_combos[:n_combinations]]

        for i, (combo, grid_score, total_score) in enumerate(scored_combos[:n_combinations], 1):
            avg_dist = self._calculate_spatial_distance(combo)
            middle_count = sum(1 for n in combo if n in self.grid_zones['middle'])
            anti_diag_count = sum(1 for n in combo if n in self.grid_zones['anti_diagonal'])
            print(f"  {i}. {list(combo)} [그리드:{grid_score:.1f}, 총점:{total_score:.1f}, 평균거리:{avg_dist:.1f}, 중간:{middle_count}, 대각:{anti_diag_count}]")

        return results

    def generate_image_based(self, n_combinations=5, seed=None, best_only=False):
        """이미지 패턴 기반 추천 (NEW)"""
        py_rng = random.Random(seed)
        print(f"\n🖼️  이미지 패턴 기반 추천")

        if best_only:
            print("  ✨ 최적 조합 모드 (랜덤 제외)")
            top_candidates = self.model.get_top_numbers(22)

            def image_score_func(combo):
                score_data = self.image_analyzer.calculate_image_score(combo)
                return score_data['total_score']

            return self._find_best_combination(top_candidates, n_combinations, custom_score_func=image_score_func, apply_phase3=True)

        combinations_list = []
        max_attempts = 10000
        attempts = 0

        top_numbers = self.model.get_top_numbers(35)

        print("  목표: 시각적 밀도 3.0~4.5, 4분면 균형, 무게중심 균형, 좌우 대칭")

        while len(combinations_list) < n_combinations and attempts < max_attempts:
            selected = py_rng.sample(top_numbers, 6)

            if self._is_valid_combination(selected):
                # 이미지 패턴 점수 계산
                image_score_data = self.image_analyzer.calculate_image_score(selected)

                # 점수가 70점 이상이면 채택
                if image_score_data['total_score'] >= 70:
                    sorted_selected = tuple(sorted(selected))
                    if sorted_selected not in combinations_list:
                        combinations_list.append((sorted_selected, image_score_data))

            attempts += 1

        # 이미지 패턴 점수로 정렬
        combinations_list.sort(key=lambda x: x[1]['total_score'], reverse=True)

        results = [list(combo) for combo, _ in combinations_list[:n_combinations]]

        for i, (combo, score_data) in enumerate(combinations_list[:n_combinations], 1):
            quad = score_data['quadrants']
            quad_str = f"Q1:{quad['Q1']}, Q2:{quad['Q2']}, Q3:{quad['Q3']}, Q4:{quad['Q4']}"
            print(f"  {i}. {list(combo)} [이미지점수:{score_data['total_score']}점, "
                  f"거리:{score_data['avg_distance']:.1f}, {quad_str}]")

        return results

    def generate_hybrid(self, n_combinations=5, seed=None, best_only=False):
        """하이브리드 추천 (여러 전략 혼합)"""
        print(f"\n⭐ 하이브리드 추천 (최고 품질)")

        if best_only:
            print("  ✨ 최적 조합 모드 (랜덤 제외 - 완전 탐색)")
            # 상위 22개 번호로 확장하여 탐색 (22C6 = 74,613)
            top_candidates = self.model.get_top_numbers(22)
            return self._find_best_combination(top_candidates, n_combinations, apply_phase3=True)

        all_combos = []

        # 각 전략에서 생성 (5가지 전략)
        score_combos = self.generate_by_score(n_combinations=2, use_top=15, seed=seed)
        prob_combos = self.generate_by_probability(n_combinations=2, seed=seed)
        pattern_combos = self.generate_by_pattern(n_combinations=2, seed=seed)
        grid_combos = self.generate_grid_based(n_combinations=2, seed=seed)
        image_combos = self.generate_image_based(n_combinations=2, seed=seed)  # NEW

        # 중복 제거하여 합치기
        for combo in score_combos + prob_combos + pattern_combos + grid_combos + image_combos:
            sorted_combo = tuple(sorted(combo))
            if sorted_combo not in all_combos:
                all_combos.append(sorted_combo)

        # 점수 계산하여 정렬
        scored = []
        for combo in all_combos:
            score = self._calculate_combination_score(combo)
            scored.append((combo, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        results = [list(combo) for combo, _ in scored[:n_combinations]]

        print(f"\n최종 선정:")
        for i, (combo, score) in enumerate(scored[:n_combinations], 1):
            odd = sum(1 for n in combo if n % 2 == 1)
            total = sum(combo)
            print(f"  {i}. {list(combo)} (점수: {score:.1f}, 합: {total}, 홀{odd}/짝{6-odd})")

        return results

    def generate_with_consecutive(self, n_combinations=5, seed=None, best_only=False):
        """관측된 연속수 패턴을 선호하는 추천"""
        py_rng = random.Random(seed)
        print(f"\n🔢 연속 번호 포함 추천")

        # 가장 많이 나온 연속 쌍
        consecutive_pairs = self.model.patterns['consecutive']['pair_frequency']
        top_pairs = sorted(consecutive_pairs.items(), key=lambda x: x[1], reverse=True)[:10]

        if best_only:
            print("  ✨ 최적 조합 모드 (랜덤 제외)")
            # 상위 3개 연속 쌍에 대해 각각 최적 조합 탐색
            best_combos = []
            top_candidates = self.model.get_top_numbers(25)

            for pair, _ in top_pairs[:3]:
                # 해당 쌍을 포함하는 조건으로 탐색
                def pair_constraint(combo):
                    return pair[0] in combo and pair[1] in combo
                best_combos.extend(self._find_best_combination(top_candidates, 1, constraint_func=pair_constraint, apply_phase3=True))

            # 그 중 최고 점수 선택
            best_combos.sort(key=lambda x: self._calculate_combination_score(x), reverse=True)
            return best_combos[:n_combinations]

        print(f"  인기 연속 쌍 활용: {[f'{p[0]}-{p[1]}' for p, _ in top_pairs[:5]]}")

        combinations_list = []
        max_attempts = 10000
        attempts = 0

        top_numbers = self.model.get_top_numbers(30)

        while len(combinations_list) < n_combinations and attempts < max_attempts:
            # 인기 연속 쌍 중 하나 선택
            pair = py_rng.choice(top_pairs)[0]
            selected = list(pair)

            # 나머지 4개 선택
            remaining = [n for n in top_numbers if n not in selected]
            if len(remaining) >= 4:
                selected.extend(py_rng.sample(remaining, 4))

            if len(selected) == 6 and self._is_valid_combination(selected):
                sorted_selected = tuple(sorted(selected))
                if sorted_selected not in combinations_list:
                    combinations_list.append(sorted_selected)

            attempts += 1

        results = [list(combo) for combo in combinations_list[:n_combinations]]

        for i, combo in enumerate(results, 1):
            # 연속 쌍 찾기
            consecutive = []
            sorted_combo = sorted(combo)
            for j in range(len(sorted_combo)-1):
                if sorted_combo[j+1] == sorted_combo[j] + 1:
                    consecutive.append(f"{sorted_combo[j]}-{sorted_combo[j+1]}")

            print(f"  {i}. {combo} [연속: {', '.join(consecutive)}]")

        return results

    def generate_random(self, n_combinations=5, seed=None, best_only=False):
        """무작위 추천 (대조군)"""
        py_rng = random.Random(seed)
        print(f"\n🎰 무작위 추천")

        if best_only:
            print("  ✨ 최적 조합 모드 (Monte Carlo 최적화)")
            # 무작위로 많이 생성해서 그 중 점수가 가장 높은 것 선택
            # 순수 랜덤보다는 '최고의 랜덤'을 찾는 방식
            return self.generate_by_score(n_combinations, use_top=45, seed=seed, best_only=False)

        combinations_list = []

        while len(combinations_list) < n_combinations:
            selected = py_rng.sample(range(1, 46), 6)
            sorted_selected = tuple(sorted(selected))
            if sorted_selected not in combinations_list:
                combinations_list.append(sorted_selected)

        results = [list(combo) for combo in combinations_list]

        for i, combo in enumerate(results, 1):
            print(f"  {i}. {combo}")

        return results

    def generate_safe_strategy(self, n_combinations=5, seed=None, best_only=False):
        """안정형(Safe) 추천 (빈도·미출현 패턴 선호)

        전략:
        1. 최근 5주간 핫넘버 + 장기 미출현 번호(출현 임박)로 '필수 그룹' 선정
        2. 필수 그룹에서 최소 2개 이상 포함하도록 강제
        3. 나머지는 점수 기반으로 채움
        """
        py_rng = random.Random(seed)
        print(f"\n🛡️ 안정형 추천 (빈도·미출현 패턴 선호)")


        # 1. 필수 그룹 선정 (약 15개)
        # 1-1. 최근 5주(35일) 핫넘버 상위 10개
        recent_data = self.model.numbers_df.head(5)
        recent_nums = []
        for _, row in recent_data.iterrows():
            recent_nums.extend(row['당첨번호'])

        hot_counter = Counter(recent_nums)
        hot_numbers = [n for n, _ in hot_counter.most_common(10)]

        # 1-2. 장기 미출현 상위 5개 (출현 임박 기대)
        missing_list = []
        for num, data in self.model.number_features.items():
            missing_list.append((num, data['absence_length']))

        missing_list.sort(key=lambda x: x[1], reverse=True)
        cold_numbers = [n for n, _ in missing_list[:5]]

        essential_pool = list(set(hot_numbers + cold_numbers))
        print(f"  필수 포함 그룹({len(essential_pool)}개): {essential_pool}")

        if best_only:
            print("  ✨ 최적 조합 모드 (랜덤 제외)")
            # 필수 그룹 + 상위 번호 합쳐서 후보군 생성
            top_general = self.model.get_top_numbers(15)
            candidates = list(set(essential_pool + top_general))

            def safe_constraint(combo):
                return sum(1 for n in combo if n in essential_pool) >= 2

            # 안정형 전략은 핫넘버를 적극 활용하므로 Phase 3의 과열 번호 필터링(제외)을 적용하지 않음 (apply_phase3=False)
            return self._find_best_combination(candidates, n_combinations, constraint_func=safe_constraint, apply_phase3=False)

        # 2. 조합 생성 (필수 그룹 2개 이상 포함)
        combinations_list = []
        max_attempts = 10000
        attempts = 0

        # 전체 상위 번호 풀 (보조용)
        top_numbers = self.model.get_top_numbers(35)

        while len(combinations_list) < n_combinations and attempts < max_attempts:
            selected = []

            # 필수 그룹에서 2~3개 선택
            n_essential = py_rng.choice([2, 3])
            if len(essential_pool) >= n_essential:
                selected.extend(py_rng.sample(essential_pool, n_essential))

            # 나머지는 전체 상위 번호에서 선택 (중복 제외)
            remaining_count = 6 - len(selected)
            pool = [n for n in top_numbers if n not in selected]

            if len(pool) >= remaining_count:
                selected.extend(py_rng.sample(pool, remaining_count))

            if len(selected) == 6 and self._is_valid_combination(selected):
                sorted_selected = tuple(sorted(selected))
                if sorted_selected not in combinations_list:
                    combinations_list.append(sorted_selected)

            attempts += 1

        # 점수 순 정렬
        scored_combos = []
        for combo in combinations_list:
            score = self._calculate_combination_score(combo)
            scored_combos.append((combo, score))

        scored_combos.sort(key=lambda x: x[1], reverse=True)

        results = [list(combo) for combo, _ in scored_combos[:n_combinations]]

        for i, (combo, score) in enumerate(scored_combos[:n_combinations], 1):
            essential_count = sum(1 for n in combo if n in essential_pool)
            print(f"  {i}. {list(combo)} (점수: {score:.1f}, 필수포함: {essential_count}개)")

        return results

    def generate_by_optimized_weights(self, n_combinations=5, seed=None, best_only=False):
        """최적화된 가중치 기반 추천

        프로세스:
        1. 최적 가중치 JSON 파일 로드
        2. 최적 가중치로 모델 재학습
        3. 점수 기반 추천 실행

        Args:
            n_combinations: 추천 개수
            seed: 랜덤 시드

        Returns:
            list: 추천 번호 조합 리스트
        """
        import os
        import json
        from prediction_model import LottoPredictionModel

        print(f"\n⚡ 최적화된 가중치 추천 (조합: {n_combinations}개)")

        # 최적 가중치 로드
        cache_dir = "../Data/backtesting_cache"
        weights_file = os.path.join(cache_dir, "optimal_weights_score.json")

        if not os.path.exists(weights_file):
            print("  ⚠️ 최적 가중치 없음, 기본 전략 사용")
            return self.generate_by_score(n_combinations, seed=seed, best_only=best_only)

        with open(weights_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        opt_weights = data['weights']
        print(f"  최적 가중치 로드 (3개 이상 일치율: {data['score']:.2f}%)")
        print(f"    freq={opt_weights['freq_weight']:.1f}, "
              f"trend={opt_weights['trend_weight']:.1f}, "
              f"absence={opt_weights['absence_weight']:.1f}, "
              f"hotness={opt_weights['hotness_weight']:.1f}")

        # 최적 가중치로 재학습
        optimized_model = LottoPredictionModel(self.loader, weights=opt_weights)
        optimized_model.train_all_patterns()

        # 추천
        temp_recommender = LottoRecommendationSystem(optimized_model)
        return temp_recommender.generate_by_score(n_combinations, seed=seed, best_only=best_only)

    def generate_ensemble(self, n_combinations=5, seed=None, best_only=False):
        """앙상블 보팅 기반 추천 (Phase 2)

        5개 전략의 추천 결과를 종합하여 다수결로 선정
        """
        np_rng = np.random.default_rng(seed)
        print(f"\n🗳️ 앙상블 보팅 추천")

        strategies = [
            self.generate_by_probability,
            self.generate_by_pattern,
            self.generate_grid_based,
            self.generate_image_based,
            self.generate_with_consecutive
        ]

        pool = []
        # 각 전략별로 10개씩 생성하여 후보군 확보
        for func in strategies:
            try:
                # 각 전략의 최적/고정 결과를 수집
                combos = func(n_combinations=10, seed=seed, best_only=best_only)
                pool.extend(combos)
            except Exception as e:
                print(f"  ⚠️ 전략 실행 중 오류: {e}")

        # 번호 빈도 분석 (투표)
        all_numbers = [num for combo in pool for num in combo]
        counter = Counter(all_numbers)

        # 정렬 기준: 1.빈도(투표수) 2.알고리즘 점수
        def sort_key(num):
            return (counter[num], self.model.number_scores[num]['total_score'])

        sorted_numbers = sorted(counter.keys(), key=sort_key, reverse=True)
        print(f"  🗳️ 투표 상위 번호: {sorted_numbers[:10]}")

        if best_only:
            print("  ✨ 최적 조합 모드 (앙상블 다수결)")
            # 투표 상위 15개 번호로 최적 조합 탐색
            return self._find_best_combination(sorted_numbers[:15], n_combinations, apply_phase3=True)


        # 빈도 가중치 기반 샘플링 (상위 25개)
        candidates = sorted_numbers[:25]
        weights = [counter[n] for n in candidates]
        total_w = sum(weights)
        probs = [w/total_w for w in weights]

        # _find_best_combination 대신 확률 기반 샘플링 구현 (다양성 위해)
        return self._find_best_combination(candidates, n_combinations) if best_only else self._sample_weighted(candidates, probs, n_combinations, rng=np_rng)

    def _sample_weighted(self, candidates, probs, n_combinations, rng=None):
        """가중치 기반 샘플링 헬퍼"""
        np_rng = rng if rng is not None else np.random.default_rng()
        results = []
        attempts = 0
        while len(results) < n_combinations and attempts < 1000:
            selected = np_rng.choice(candidates, 6, replace=False, p=probs)
            if self._is_valid_combination(selected):
                sorted_selected = list(sorted(selected))
                if sorted_selected not in results:
                    results.append(sorted_selected)
            attempts += 1
        return results

    def get_swap_candidates(self, current_combination, number_to_remove, top_n=5):
        """교체 후보 추천 (Phase 4: 사용자 인터랙티브 튜닝)"""
        current_score = self._calculate_combination_score(current_combination)
        remaining_nums = [n for n in current_combination if n != number_to_remove]

        # 후보군: 상위 45개(전체) 중 현재 조합에 없는 것
        # (이미 점수순으로 정렬된 상태에서 필터링)
        candidates = [n for n in self.model.get_top_numbers(45) if n not in current_combination]

        recommendations = []
        for cand in candidates:
            new_combo = sorted(remaining_nums + [cand])

            # 유효성 검사
            if not self._is_valid_combination(new_combo):
                continue

            # Phase 3 제약조건 확인 (고정 모드 튜닝이므로 안전장치 적용)
            if not self._check_phase3_constraints(new_combo):
                continue

            new_score = self._calculate_combination_score(new_combo)
            diff = new_score - current_score

            recommendations.append({
                'number': cand,
                'new_score': new_score,
                'diff': diff
            })

        # 점수 높은 순 정렬
        recommendations.sort(key=lambda x: x['new_score'], reverse=True)
        return recommendations[:top_n]

    def generate_all_strategies(self, n_per_strategy=3, seed=None):
        """모든 전략으로 번호 생성"""
        print("\n" + "="*70)
        print("🎯 로또 645 번호 추천 시스템")
        print("="*70)

        results = {
            'hybrid': self.generate_hybrid(n_per_strategy, seed=seed),
            'score': self.generate_by_score(n_per_strategy, seed=seed),
            'probability': self.generate_by_probability(n_per_strategy, seed=seed),
            'pattern': self.generate_by_pattern(n_per_strategy, seed=seed),
            'grid': self.generate_grid_based(n_per_strategy, seed=seed),
            'image': self.generate_image_based(n_per_strategy, seed=seed),  # NEW
            'consecutive': self.generate_with_consecutive(n_per_strategy, seed=seed),
            'safe': self.generate_safe_strategy(n_per_strategy, seed=seed), # NEW
            'random': self.generate_random(n_per_strategy, seed=seed)
        }

        print("\n" + "="*70)
        print("✅ 추천 완료")
        print("="*70)

        return results


def main():
    """테스트용 메인 함수"""
    from data_loader import LottoDataLoader
    from prediction_model import LottoPredictionModel

    data_path = "../Data/645_251227.csv"

    print("데이터 로딩 및 모델 학습 중...")
    loader = LottoDataLoader(data_path)
    loader.load_data()
    loader.preprocess()
    loader.extract_numbers()

    model = LottoPredictionModel(loader)
    model.train_all_patterns()

    # 추천 시스템 실행
    recommender = LottoRecommendationSystem(model)
    recommendations = recommender.generate_all_strategies(n_per_strategy=3)

    print("\n\n📋 추천 요약:")
    print("="*70)
    for strategy, combos in recommendations.items():
        print(f"\n[{strategy.upper()}]")
        for i, combo in enumerate(combos, 1):
            print(f"  {i}. {combo}")


if __name__ == "__main__":
    main()
