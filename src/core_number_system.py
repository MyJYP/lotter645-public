"""
코어 번호 추천 시스템
핵심 번호 3-4개를 추출하고 조합 생성
"""
import numpy as np
import random
from itertools import combinations


class CoreNumberSystem:
    """코어 번호 추천 시스템"""

    def __init__(self, prediction_model, recommendation_system):
        """
        Args:
            prediction_model: LottoPredictionModel 인스턴스
            recommendation_system: LottoRecommendationSystem 인스턴스
        """
        self.model = prediction_model
        self.recommender = recommendation_system
        self.loader = prediction_model.loader

    def calculate_confidence_scores(self):
        """
        모든 번호(1-45)의 신뢰도 점수 계산

        Returns:
            dict: {번호: {'score': 점수, 'confidence': 신뢰도%}}
        """
        confidence_scores = {}

        # 모든 번호의 점수 가져오기
        all_scores = []
        for num in range(1, 46):
            score = self.model.number_scores[num]['total_score']
            all_scores.append(score)

        max_score = max(all_scores)
        min_score = min(all_scores)

        # 정규화하여 신뢰도 계산 (50% ~ 100%)
        for num in range(1, 46):
            score = self.model.number_scores[num]['total_score']
            # 정규화: 50% ~ 100% 범위로 매핑
            if max_score == min_score:
                confidence = 75.0
            else:
                confidence = 50 + ((score - min_score) / (max_score - min_score)) * 50

            confidence_scores[num] = {
                'score': score,
                'confidence': confidence,
                'rank': 0  # 나중에 설정
            }

        # 순위 계산
        sorted_numbers = sorted(confidence_scores.items(),
                               key=lambda x: x[1]['score'],
                               reverse=True)

        for rank, (num, data) in enumerate(sorted_numbers, 1):
            confidence_scores[num]['rank'] = rank

        return confidence_scores

    def get_core_numbers(self, n_core=4, min_confidence=85):
        """
        코어 번호 추출 (가장 확신하는 핵심 번호)

        Args:
            n_core: 코어 번호 개수 (기본 4개)
            min_confidence: 최소 신뢰도 (기본 85%)

        Returns:
            list: 코어 번호 리스트
        """
        confidence_scores = self.calculate_confidence_scores()

        # 신뢰도 높은 순으로 정렬
        sorted_numbers = sorted(
            confidence_scores.items(),
            key=lambda x: x[1]['confidence'],
            reverse=True
        )

        # 신뢰도 기준 충족하는 번호 중 상위 n_core개
        core_numbers = []
        for num, data in sorted_numbers:
            if data['confidence'] >= min_confidence or len(core_numbers) < n_core:
                core_numbers.append(num)
                if len(core_numbers) >= n_core:
                    break

        return sorted(core_numbers), confidence_scores

    def generate_with_core(self, core_numbers, n_combinations=5, seed=None):
        """
        코어 번호를 포함한 조합 생성

        Args:
            core_numbers: 코어 번호 리스트 (3-4개)
            n_combinations: 생성할 조합 개수
            seed: 랜덤 시드

        Returns:
            list: 조합 리스트
        """
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        n_core = len(core_numbers)
        n_remaining = 6 - n_core

        # 나머지 번호 풀 (코어 제외)
        remaining_pool = [n for n in range(1, 46) if n not in core_numbers]

        # 상위 번호 우선 (코어 제외)
        top_numbers = [n for n in self.model.get_top_numbers(30)
                       if n not in core_numbers]

        # 상위 번호 풀이 부족하면 전체 풀 사용
        if len(top_numbers) < n_remaining:
            candidate_pool = remaining_pool
        else:
            candidate_pool = top_numbers

        combinations_list = []
        max_attempts = 10000
        attempts = 0

        while len(combinations_list) < n_combinations and attempts < max_attempts:
            # 나머지 번호 선택
            remaining = random.sample(candidate_pool, n_remaining)

            # 코어 + 나머지 조합
            selected = core_numbers + remaining

            if self.recommender._is_valid_combination(selected):
                sorted_selected = tuple(sorted(selected))
                if sorted_selected not in combinations_list:
                    combinations_list.append(sorted_selected)

            attempts += 1

        # 점수로 정렬
        scored = []
        for combo in combinations_list:
            score = self.recommender._calculate_combination_score(combo)
            scored.append((combo, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        results = [list(combo) for combo, _ in scored[:n_combinations]]

        return results

    def generate_with_fixed(self, fixed_numbers, n_combinations=5, seed=None):
        """
        사용자 지정 고정 번호를 포함한 조합 생성

        Args:
            fixed_numbers: 사용자가 고정한 번호 리스트 (1-5개)
            n_combinations: 생성할 조합 개수
            seed: 랜덤 시드

        Returns:
            list: 조합 리스트
        """
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        n_fixed = len(fixed_numbers)

        if n_fixed >= 6:
            # 이미 6개면 그대로 반환
            return [sorted(fixed_numbers)]

        n_remaining = 6 - n_fixed

        # 나머지 번호 풀 (고정 번호 제외)
        remaining_pool = [n for n in range(1, 46) if n not in fixed_numbers]

        # 상위 번호 우선 (고정 번호 제외)
        top_numbers = [n for n in self.model.get_top_numbers(35)
                       if n not in fixed_numbers]

        if len(top_numbers) < n_remaining:
            candidate_pool = remaining_pool
        else:
            candidate_pool = top_numbers

        combinations_list = []
        max_attempts = 10000
        attempts = 0

        while len(combinations_list) < n_combinations and attempts < max_attempts:
            # 나머지 번호 선택
            remaining = random.sample(candidate_pool, n_remaining)

            # 고정 + 나머지 조합
            selected = fixed_numbers + remaining

            if self.recommender._is_valid_combination(selected):
                sorted_selected = tuple(sorted(selected))
                if sorted_selected not in combinations_list:
                    combinations_list.append(sorted_selected)

            attempts += 1

        # 점수로 정렬
        scored = []
        for combo in combinations_list:
            score = self.recommender._calculate_combination_score(combo)
            scored.append((combo, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        results = [list(combo) for combo, _ in scored[:n_combinations]]

        return results

    def analyze_core_coverage(self, core_numbers):
        """
        코어 번호가 과거 당첨번호에 얼마나 포함되었는지 분석

        Args:
            core_numbers: 코어 번호 리스트

        Returns:
            dict: 분석 결과
        """
        total_rounds = len(self.loader.numbers_df)
        coverage_stats = {
            'all_matched': 0,  # 코어 전체 포함
            'partial_matched': {},  # 부분 일치 (1개, 2개, 3개...)
            'none_matched': 0,  # 전혀 없음
            'match_history': []  # 매칭 이력
        }

        n_core = len(core_numbers)
        for i in range(n_core + 1):
            coverage_stats['partial_matched'][i] = 0

        for _, row in self.loader.numbers_df.iterrows():
            winning = row['당첨번호']
            matched = [num for num in core_numbers if num in winning]
            n_matched = len(matched)

            coverage_stats['partial_matched'][n_matched] += 1

            if n_matched == n_core:
                coverage_stats['all_matched'] += 1
                coverage_stats['match_history'].append({
                    '회차': row['회차'],
                    '일자': row['일자'],
                    '매칭': matched,
                    '당첨번호': list(winning)
                })
            elif n_matched == 0:
                coverage_stats['none_matched'] += 1

        # 비율 계산
        coverage_stats['all_matched_rate'] = coverage_stats['all_matched'] / total_rounds * 100
        coverage_stats['none_matched_rate'] = coverage_stats['none_matched'] / total_rounds * 100

        for i in range(n_core + 1):
            count = coverage_stats['partial_matched'][i]
            coverage_stats['partial_matched'][i] = {
                'count': count,
                'rate': count / total_rounds * 100
            }

        return coverage_stats

    def get_complementary_numbers(self, fixed_numbers, top_n=10):
        """
        고정 번호와 잘 어울리는 보완 번호 추천

        Args:
            fixed_numbers: 고정 번호 리스트
            top_n: 추천할 보완 번호 개수

        Returns:
            list: [(번호, 동반출현횟수, 점수), ...]
        """
        from collections import Counter

        # 고정 번호와 함께 나온 번호 카운트
        companion_counts = Counter()

        for _, row in self.loader.numbers_df.iterrows():
            winning = row['당첨번호']

            # 고정 번호가 하나라도 포함되면
            if any(num in winning for num in fixed_numbers):
                # 나머지 번호들 카운트 (고정 번호 제외)
                for num in winning:
                    if num not in fixed_numbers:
                        companion_counts[num] += 1

        # 점수와 결합하여 정렬
        complementary = []
        for num, count in companion_counts.items():
            score = self.model.number_scores[num]['total_score']
            combined_score = count * 0.5 + score * 0.5  # 동반출현과 점수 균형
            complementary.append((num, count, score, combined_score))

        # 결합 점수로 정렬
        complementary.sort(key=lambda x: x[3], reverse=True)

        return complementary[:top_n]


if __name__ == "__main__":
    from data_loader import LottoDataLoader
    from prediction_model import LottoPredictionModel
    from recommendation_system import LottoRecommendationSystem

    print("\n" + "="*80)
    print("🎯 코어 번호 추천 시스템 테스트")
    print("="*80)

    # 데이터 로드
    data_path = "../Data/645_251227.csv"
    loader = LottoDataLoader(data_path)
    loader.load_data()
    loader.preprocess()
    loader.extract_numbers()

    # 모델 학습
    print("\n모델 학습 중...")
    model = LottoPredictionModel(loader)
    model.train_all_patterns()

    recommender = LottoRecommendationSystem(model)

    # 코어 시스템 초기화
    core_system = CoreNumberSystem(model, recommender)

    # 1. 신뢰도 점수 계산
    print("\n" + "="*80)
    print("📊 번호별 신뢰도 점수 TOP 10")
    print("="*80)

    confidence_scores = core_system.calculate_confidence_scores()
    sorted_by_confidence = sorted(
        confidence_scores.items(),
        key=lambda x: x[1]['confidence'],
        reverse=True
    )

    for i, (num, data) in enumerate(sorted_by_confidence[:10], 1):
        print(f"{i:2d}. 번호 {num:2d}: 신뢰도 {data['confidence']:.1f}%, "
              f"점수 {data['score']:.1f}, 순위 {data['rank']}")

    # 2. 코어 번호 추출
    print("\n" + "="*80)
    print("⭐ 코어 번호 추출 (4개)")
    print("="*80)

    core_numbers, _ = core_system.get_core_numbers(n_core=4, min_confidence=85)
    print(f"\n추출된 코어 번호: {core_numbers}")

    # 코어 커버리지 분석
    coverage = core_system.analyze_core_coverage(core_numbers)
    print(f"\n과거 데이터 분석:")
    print(f"  - 코어 전체 포함: {coverage['all_matched']}회 ({coverage['all_matched_rate']:.2f}%)")
    print(f"  - 3개 이상 포함: {coverage['partial_matched'][3]['count'] + coverage['partial_matched'][4]['count']}회")
    print(f"  - 전혀 없음: {coverage['none_matched']}회 ({coverage['none_matched_rate']:.2f}%)")

    # 3. 코어 번호 포함 조합 생성
    print("\n" + "="*80)
    print("🎲 코어 번호 포함 추천 조합 (5개)")
    print("="*80)

    core_combos = core_system.generate_with_core(core_numbers, n_combinations=5)

    for i, combo in enumerate(core_combos, 1):
        core_str = ', '.join([f"**{n}**" if n in core_numbers else str(n) for n in combo])
        print(f"{i}. [{core_str}]")

    # 4. 고정 번호 + 추천
    print("\n" + "="*80)
    print("🔒 고정 번호 + 추천 조합")
    print("="*80)

    fixed = [7, 12]  # 사용자가 고정한 번호
    print(f"\n사용자 고정 번호: {fixed}")

    # 보완 번호 추천
    complementary = core_system.get_complementary_numbers(fixed, top_n=10)
    print(f"\n추천 보완 번호 TOP 10:")
    for i, (num, count, score, combined) in enumerate(complementary, 1):
        print(f"  {i:2d}. 번호 {num:2d}: 동반출현 {count}회, 점수 {score:.1f}")

    fixed_combos = core_system.generate_with_fixed(fixed, n_combinations=5)

    print(f"\n고정 번호 포함 추천 조합:")
    for i, combo in enumerate(fixed_combos, 1):
        fixed_str = ', '.join([f"**{n}**" if n in fixed else str(n) for n in combo])
        print(f"{i}. [{fixed_str}]")

    print("\n" + "="*80)
    print("✅ 테스트 완료")
    print("="*80)
