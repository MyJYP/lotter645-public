"""
로또 645 예측 모델 모듈
다양한 접근법으로 번호 패턴 분석 및 특징 추출
"""
import pandas as pd
import numpy as np
from collections import Counter, defaultdict
from data_loader import normalize_draw_history
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')


class LottoPredictionModel:
    """로또 번호 예측을 위한 머신러닝 모델"""

    def __init__(self, data_loader, weights=None):
        """
        Args:
            data_loader: LottoDataLoader 인스턴스
            weights: dict 또는 None
                {
                    'freq_weight': 30.0,      # 빈도 가중치 (기본 30)
                    'trend_weight': 30.0,     # 트렌드 가중치 (기본 30)
                    'absence_weight': 20.0,   # 부재기간 가중치 (기본 20)
                    'hotness_weight': 20.0    # 핫넘버 가중치 (기본 20)
                }
        """
        self.loader = data_loader
        self.df = data_loader.df
        self.numbers_df = normalize_draw_history(data_loader.numbers_df)

        # 가중치 설정 (기본값 또는 사용자 지정)
        if weights is None:
            self.weights = {
                'freq_weight': 30.0,
                'trend_weight': 30.0,
                'absence_weight': 20.0,
                'hotness_weight': 20.0
            }
        else:
            self.weights = weights

        # 모델 컴포넌트
        self.scaler = StandardScaler()
        self.models = {}

        # 분석 결과 저장
        self.number_features = {}
        self.patterns = {}

    def extract_number_features(self):
        """각 번호(1-45)에 대한 특징 추출"""
        print("\n📊 번호별 특징 추출 중...")

        self.numbers_df = normalize_draw_history(self.numbers_df)
        if self.numbers_df.empty:
            raise ValueError('패턴 분석에 사용할 과거 회차가 없습니다.')
        all_numbers = [n for numbers in self.numbers_df['당첨번호'] for n in numbers]
        frequency = Counter(all_numbers)
        latest_round = int(self.numbers_df['회차'].max())
        observed_span = latest_round - int(self.numbers_df['회차'].min()) + 1

        features = {}

        for num in range(1, 46):
            # 1. 전체 출현 빈도
            total_freq = frequency.get(num, 0)

            # 2. 최근 100회차 출현 빈도
            recent_100 = []
            for _, row in self.numbers_df.head(100).iterrows():
                if num in row['당첨번호']:
                    recent_100.append(1)
                else:
                    recent_100.append(0)
            recent_freq = sum(recent_100)

            # 3. 최근 50회차 출현 빈도
            recent_50 = []
            for _, row in self.numbers_df.head(50).iterrows():
                if num in row['당첨번호']:
                    recent_50.append(1)
                else:
                    recent_50.append(0)
            recent_50_freq = sum(recent_50)

            # 4. 마지막 출현 이후 경과 회차
            appearances = [int(row['회차']) for _, row in self.numbers_df.iterrows()
                           if num in row['당첨번호']]
            absence_length = latest_round - appearances[0] if appearances else observed_span

            # 관측 회차 값의 차를 사용한다. 누락 회차의 출현 여부는 알 수 없다.
            intervals = [a - b for a, b in zip(appearances, appearances[1:])]
            avg_interval = float(np.mean(intervals)) if intervals else 0.0
            std_interval = float(np.std(intervals)) if intervals else 0.0

            # 6. 구간 (저/중/고)
            if 1 <= num <= 15:
                section = 0  # 저구간
            elif 16 <= num <= 30:
                section = 1  # 중구간
            else:
                section = 2  # 고구간

            # 7. 홀짝
            odd_even = num % 2

            features[num] = {
                'number': num,
                'total_frequency': total_freq,
                'recent_100_frequency': recent_freq,
                'recent_50_frequency': recent_50_freq,
                'absence_length': absence_length,
                'avg_interval': avg_interval,
                'std_interval': std_interval,
                'appearance_count': len(appearances),
                'absence_is_observation_bound': not appearances or observed_span != len(self.numbers_df),
                'section': section,
                'odd_even': odd_even,
                'hotness_score': recent_50_freq / (absence_length + 1) * 100  # 핫넘버 점수
            }

        self.number_features = features
        print(f"✓ 45개 번호에 대한 특징 추출 완료")
        return features

    def analyze_consecutive_patterns(self):
        """연속 번호 패턴 분석"""
        print("📊 연속 번호 패턴 학습 중...")

        consecutive_stats = {
            'pair_frequency': defaultdict(int),  # 2개 연속
            'triplet_frequency': defaultdict(int),  # 3개 연속
            'has_consecutive_prob': 0
        }

        has_consecutive_count = 0

        for _, row in self.numbers_df.iterrows():
            nums = sorted(row['당첨번호'])
            has_consecutive = False

            for i in range(len(nums)-1):
                if nums[i+1] == nums[i] + 1:
                    has_consecutive = True
                    # 2개 연속
                    pair = (nums[i], nums[i+1])
                    consecutive_stats['pair_frequency'][pair] += 1

                    # 3개 연속 확인
                    if i < len(nums)-2 and nums[i+2] == nums[i+1] + 1:
                        triplet = (nums[i], nums[i+1], nums[i+2])
                        consecutive_stats['triplet_frequency'][triplet] += 1

            if has_consecutive:
                has_consecutive_count += 1

        consecutive_stats['has_consecutive_prob'] = has_consecutive_count / len(self.numbers_df)

        self.patterns['consecutive'] = consecutive_stats
        print(f"✓ 연속 번호 출현 확률: {consecutive_stats['has_consecutive_prob']*100:.1f}%")
        return consecutive_stats

    def analyze_section_patterns(self):
        """구간별 출현 패턴 분석"""
        print("📊 구간 패턴 학습 중...")

        section_patterns = {
            'distribution': [],  # [저구간개수, 중구간개수, 고구간개수]
            'most_common': None
        }

        for _, row in self.numbers_df.iterrows():
            nums = row['당첨번호']
            low = sum(1 for n in nums if 1 <= n <= 15)
            mid = sum(1 for n in nums if 16 <= n <= 30)
            high = sum(1 for n in nums if 31 <= n <= 45)

            section_patterns['distribution'].append((low, mid, high))

        # 가장 흔한 구간 분포
        dist_counter = Counter(section_patterns['distribution'])
        section_patterns['most_common'] = dist_counter.most_common(10)

        self.patterns['section'] = section_patterns
        print(f"✓ 가장 흔한 구간 분포: {section_patterns['most_common'][0]}")
        return section_patterns

    def analyze_odd_even_patterns(self):
        """홀짝 패턴 분석"""
        print("📊 홀짝 패턴 학습 중...")

        odd_even_patterns = {
            'distribution': [],
            'most_common': None
        }

        for _, row in self.numbers_df.iterrows():
            nums = row['당첨번호']
            odd = sum(1 for n in nums if n % 2 == 1)
            even = 6 - odd

            odd_even_patterns['distribution'].append((odd, even))

        dist_counter = Counter(odd_even_patterns['distribution'])
        odd_even_patterns['most_common'] = dist_counter.most_common(5)

        self.patterns['odd_even'] = odd_even_patterns
        print(f"✓ 가장 흔한 홀짝 분포: {odd_even_patterns['most_common'][0]}")
        return odd_even_patterns

    def analyze_sum_patterns(self):
        """번호 합계 패턴 분석"""
        print("📊 합계 패턴 학습 중...")

        sums = []
        for _, row in self.numbers_df.iterrows():
            total = sum(row['당첨번호'])
            sums.append(total)

        sum_patterns = {
            'mean': np.mean(sums),
            'std': np.std(sums),
            'median': np.median(sums),
            'min': np.min(sums),
            'max': np.max(sums),
            'q1': np.percentile(sums, 25),
            'q3': np.percentile(sums, 75)
        }

        self.patterns['sum'] = sum_patterns
        print(f"✓ 합계 평균: {sum_patterns['mean']:.1f}, 표준편차: {sum_patterns['std']:.1f}")
        return sum_patterns

    def calculate_number_scores(self):
        """각 번호에 대한 종합 점수 계산 (가중치 적용)"""
        print("\n🎯 번호별 종합 점수 계산 중...")

        if not self.number_features:
            self.extract_number_features()

        scores = {}

        # 가중치 추출
        freq_w = self.weights['freq_weight']
        trend_w = self.weights['trend_weight']
        absence_w = self.weights['absence_weight']
        hotness_w = self.weights['hotness_weight']

        for num in range(1, 46):
            features = self.number_features[num]

            # 점수 계산 (여러 요소 종합, 가중치 적용)
            # 1. 빈도 점수 (0-freq_w점)
            freq_score = min(features['total_frequency'] / 100 * freq_w, freq_w)

            # 2. 최근 트렌드 점수 (0-trend_w점)
            trend_score = features['recent_50_frequency'] / 50 * trend_w

            # 3. 부재 기간 점수 (0-absence_w점) - 오래 안나왔으면 높은 점수
            absence_score = min(features['absence_length'] / 20 * absence_w, absence_w)

            # 4. 핫넘버 점수 (0-hotness_w점)
            hotness_score = min(features['hotness_score'] / 10 * hotness_w, hotness_w)

            total_score = freq_score + trend_score + absence_score + hotness_score

            scores[num] = {
                'total_score': total_score,
                'freq_score': freq_score,
                'trend_score': trend_score,
                'absence_score': absence_score,
                'hotness_score': hotness_score,
                'features': features
            }

        # 점수 순으로 정렬
        sorted_scores = sorted(scores.items(), key=lambda x: x[1]['total_score'], reverse=True)

        print(f"\n상위 10개 번호:")
        for i, (num, score) in enumerate(sorted_scores[:10], 1):
            print(f"  {i}. 번호 {num:2d}: {score['total_score']:.1f}점")

        self.number_scores = scores
        return scores

    def train_all_patterns(self):
        """모든 패턴 학습"""
        print("\n" + "="*70)
        print("🤖 머신러닝 모델 학습 시작")
        print("="*70)

        self.extract_number_features()
        self.analyze_consecutive_patterns()
        self.analyze_section_patterns()
        self.analyze_odd_even_patterns()
        self.analyze_sum_patterns()
        self.calculate_number_scores()

        print("\n" + "="*70)
        print("✅ 모델 학습 완료")
        print("="*70)

        return {
            'number_features': self.number_features,
            'patterns': self.patterns,
            'scores': self.number_scores
        }

    def get_top_numbers(self, n=20):
        """점수 기반 상위 N개 번호 반환"""
        if not hasattr(self, 'number_scores'):
            self.calculate_number_scores()

        sorted_scores = sorted(self.number_scores.items(),
                             key=lambda x: x[1]['total_score'],
                             reverse=True)

        return [num for num, _ in sorted_scores[:n]]

    def get_probability_weights(self):
        """각 번호의 확률 가중치 계산"""
        if not hasattr(self, 'number_scores'):
            self.calculate_number_scores()

        weights = {}
        total_score = sum(score['total_score'] for score in self.number_scores.values())

        for num, score in self.number_scores.items():
            weights[num] = score['total_score'] / total_score if total_score > 0 else 1/45

        return weights

    def evaluate_recent_performance(self, n_rounds=10):
        """최근 회차에 대한 모델 성능(적합도) 평가

        현재 학습된 모델의 상위 추천 번호(Top 6)가 최근 회차 결과와
        얼마나 일치하는지 분석하여 모델의 최신 트렌드 반영도를 측정합니다.
        """
        print(f"\n📊 최근 {n_rounds}회차 성능 평가 중...")

        recent_data = self.numbers_df.head(n_rounds)

        # 현재 모델의 Top 6 번호 (고정)
        top_6 = set(self.get_top_numbers(6))

        results = []
        total_prize = 0
        total_cost = n_rounds * 1000

        # 등수별 당첨금 (대략적인 평균값)
        prizes = {
            1: 2000000000,
            2: 50000000,
            3: 1500000,
            4: 50000,
            5: 5000,
            0: 0
        }

        for _, row in recent_data.iterrows():
            round_num = row['회차']
            winning_nums = set(row['당첨번호'])
            bonus_num = row['보너스번호']

            # 매칭 개수 확인
            matched = len(winning_nums & top_6)
            is_bonus = bonus_num in top_6

            # 등수 판별
            rank = 0
            if matched == 6: rank = 1
            elif matched == 5 and is_bonus: rank = 2
            elif matched == 5: rank = 3
            elif matched == 4: rank = 4
            elif matched == 3: rank = 5

            prize = prizes.get(rank, 0)
            total_prize += prize

            # 당첨 번호들의 평균 점수 (모델의 확신도)
            avg_score = np.mean([self.number_scores[n]['total_score'] for n in winning_nums]) if hasattr(self, 'number_scores') else 0

            results.append({
                'round': round_num,
                'matched': matched,
                'rank': rank,
                'prize': prize,
                'avg_score': avg_score
            })

        avg_match = sum(r['matched'] for r in results) / n_rounds
        roi = (total_prize - total_cost) / total_cost * 100 if total_cost > 0 else 0

        return {
            'avg_match': avg_match,
            'roi': roi,
            'total_prize': total_prize,
            'details': results
        }


def main():
    """테스트용 메인 함수"""
    from data_loader import LottoDataLoader

    data_path = "../Data/645_251227.csv"

    print("데이터 로딩 중...")
    loader = LottoDataLoader(data_path)
    loader.load_data()
    loader.preprocess()
    loader.extract_numbers()

    # 예측 모델 학습
    model = LottoPredictionModel(loader)
    results = model.train_all_patterns()

    # 상위 번호 출력
    print("\n추천 번호 후보 (상위 20개):")
    top_numbers = model.get_top_numbers(20)
    print(top_numbers)


if __name__ == "__main__":
    main()
