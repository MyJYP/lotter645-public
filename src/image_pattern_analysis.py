"""
복권 용지 이미지 패턴 분석
생성된 복권용지 이미지들의 시각적 패턴을 분석
"""
import numpy as np
import pandas as pd
from collections import Counter, defaultdict
from PIL import Image
import os
import glob


class ImagePatternAnalysis:
    """복권 용지 이미지 패턴 분석 클래스"""

    def __init__(self, loader):
        """
        Args:
            loader: LottoDataLoader 인스턴스
        """
        self.loader = loader
        self.images_folder = "../images"

        # 7x7 그리드 매핑
        self.position_to_number = {}
        self.number_to_position = {}
        for num in range(1, 46):
            row = (num - 1) // 7
            col = (num - 1) % 7
            self.position_to_number[(row, col)] = num
            self.number_to_position[num] = (row, col)

    def analyze_visual_density(self):
        """
        마킹된 번호들의 시각적 밀도 분석
        복권용지 상에서 번호들이 얼마나 밀집되어 있는지 분석
        """
        print("\n" + "=" * 70)
        print("🎨 시각적 밀도 분석")
        print("=" * 70)

        density_scores = []

        for _, row in self.loader.numbers_df.iterrows():
            numbers = sorted(row['당첨번호'])
            positions = [self.number_to_position[num] for num in numbers]

            # 각 번호 쌍 간의 유클리드 거리 계산
            distances = []
            for i in range(len(positions)):
                for j in range(i + 1, len(positions)):
                    r1, c1 = positions[i]
                    r2, c2 = positions[j]
                    dist = np.sqrt((r2 - r1) ** 2 + (c2 - c1) ** 2)
                    distances.append(dist)

            avg_distance = np.mean(distances)
            density_scores.append({
                '회차': row['회차'],
                '평균_거리': avg_distance,
                '밀도': 1 / avg_distance  # 거리의 역수 = 밀도
            })

        df = pd.DataFrame(density_scores)

        print(f"\n평균 시각적 거리: {df['평균_거리'].mean():.2f}")
        print(f"최소 거리 (가장 밀집): {df['평균_거리'].min():.2f}")
        print(f"최대 거리 (가장 분산): {df['평균_거리'].max():.2f}")
        print(f"표준편차: {df['평균_거리'].std():.2f}")

        # 가장 밀집된 회차 TOP 5
        print("\n🔥 가장 밀집된 회차 TOP 5 (번호들이 가까움):")
        top_dense = df.nsmallest(5, '평균_거리')
        for idx, row in top_dense.iterrows():
            print(f"  {int(row['회차'])}회차 - 평균 거리: {row['평균_거리']:.2f}")

        # 가장 분산된 회차 TOP 5
        print("\n🌊 가장 분산된 회차 TOP 5 (번호들이 멀리 떨어짐):")
        top_sparse = df.nlargest(5, '평균_거리')
        for idx, row in top_sparse.iterrows():
            print(f"  {int(row['회차'])}회차 - 평균 거리: {row['평균_거리']:.2f}")

        return df

    def analyze_quadrant_patterns(self):
        """
        복권용지를 4등분하여 각 분면의 번호 분포 분석
        """
        print("\n" + "=" * 70)
        print("📐 4분면 패턴 분석")
        print("=" * 70)

        quadrant_counts = defaultdict(lambda: defaultdict(int))

        for _, row in self.loader.numbers_df.iterrows():
            numbers = row['당첨번호']
            quadrants = {'Q1': 0, 'Q2': 0, 'Q3': 0, 'Q4': 0}

            for num in numbers:
                r, c = self.number_to_position[num]
                # Q1: 왼쪽 위 (row < 3.5, col < 3.5)
                # Q2: 오른쪽 위 (row < 3.5, col >= 3.5)
                # Q3: 왼쪽 아래 (row >= 3.5, col < 3.5)
                # Q4: 오른쪽 아래 (row >= 3.5, col >= 3.5)

                if r < 3.5 and c < 3.5:
                    quadrants['Q1'] += 1
                elif r < 3.5 and c >= 3.5:
                    quadrants['Q2'] += 1
                elif r >= 3.5 and c < 3.5:
                    quadrants['Q3'] += 1
                else:
                    quadrants['Q4'] += 1

            # 패턴 기록 (예: "2-1-2-1" = Q1에 2개, Q2에 1개, Q3에 2개, Q4에 1개)
            pattern = f"{quadrants['Q1']}-{quadrants['Q2']}-{quadrants['Q3']}-{quadrants['Q4']}"
            quadrant_counts[pattern][tuple(sorted(quadrants.items()))] += 1

        # 가장 흔한 4분면 패턴
        pattern_freq = Counter()
        for pattern in quadrant_counts:
            total = sum(quadrant_counts[pattern].values())
            pattern_freq[pattern] = total

        print("\n가장 흔한 4분면 분포 패턴 TOP 10:")
        print("  (Q1-Q2-Q3-Q4 형식: 왼쪽위-오른쪽위-왼쪽아래-오른쪽아래)")
        print()
        for pattern, count in pattern_freq.most_common(10):
            percentage = count / len(self.loader.numbers_df) * 100
            print(f"  {pattern}: {count}회 ({percentage:.1f}%)")

        # Q1, Q2, Q3, Q4 번호 범위 표시
        print("\n📋 4분면 번호 구성:")
        print("  Q1 (왼쪽 위):    1-3, 8-10, 15-17")
        print("  Q2 (오른쪽 위):  4-7, 11-14, 18-21")
        print("  Q3 (왼쪽 아래):  22-24, 29-31, 36-38, 43-45")
        print("  Q4 (오른쪽 아래): 25-28, 32-35, 39-42")

        return pattern_freq

    def analyze_visual_balance(self):
        """
        시각적 균형 분석 - 번호들의 무게중심 분석
        """
        print("\n" + "=" * 70)
        print("⚖️  시각적 균형 분석 (무게중심)")
        print("=" * 70)

        center_of_mass_data = []

        for _, row in self.loader.numbers_df.iterrows():
            numbers = row['당첨번호']
            positions = [self.number_to_position[num] for num in numbers]

            # 무게중심 계산
            center_row = np.mean([p[0] for p in positions])
            center_col = np.mean([p[1] for p in positions])

            # 이상적인 중심 (3, 3)
            ideal_row, ideal_col = 3, 3
            deviation = np.sqrt((center_row - ideal_row) ** 2 + (center_col - ideal_col) ** 2)

            center_of_mass_data.append({
                '회차': row['회차'],
                '중심_row': center_row,
                '중심_col': center_col,
                '이상중심_편차': deviation
            })

        df = pd.DataFrame(center_of_mass_data)

        print(f"\n평균 무게중심: ({df['중심_row'].mean():.2f}, {df['중심_col'].mean():.2f})")
        print(f"이상적 중심 (3, 3)으로부터 평균 편차: {df['이상중심_편차'].mean():.2f}")
        print(f"최소 편차 (가장 균형잡힘): {df['이상중심_편차'].min():.2f}")
        print(f"최대 편차 (가장 불균형): {df['이상중심_편차'].max():.2f}")

        # 가장 균형잡힌 회차 TOP 5
        print("\n⚖️  가장 균형잡힌 회차 TOP 5:")
        balanced = df.nsmallest(5, '이상중심_편차')
        for idx, row in balanced.iterrows():
            print(f"  {int(row['회차'])}회차 - 편차: {row['이상중심_편차']:.2f}, "
                  f"중심: ({row['중심_row']:.1f}, {row['중심_col']:.1f})")

        return df

    def analyze_symmetry_patterns(self):
        """
        대칭 패턴 분석 - 좌우/상하 대칭성
        """
        print("\n" + "=" * 70)
        print("🔄 대칭 패턴 분석")
        print("=" * 70)

        symmetry_stats = {
            '좌우_대칭': 0,
            '상하_대칭': 0,
            '대각선_대칭': 0,
            '비대칭': 0
        }

        for _, row in self.loader.numbers_df.iterrows():
            numbers = row['당첨번호']
            positions = [self.number_to_position[num] for num in numbers]

            # 좌우 대칭 검사 (col 기준)
            left_count = sum(1 for r, c in positions if c < 3)
            right_count = sum(1 for r, c in positions if c > 3)
            lr_symmetric = abs(left_count - right_count) <= 1

            # 상하 대칭 검사 (row 기준)
            top_count = sum(1 for r, c in positions if r < 3)
            bottom_count = sum(1 for r, c in positions if r > 3)
            tb_symmetric = abs(top_count - bottom_count) <= 1

            # 대각선 대칭 검사
            diag_diff = sum(abs(r - c) for r, c in positions)
            diag_symmetric = diag_diff < 6

            if lr_symmetric:
                symmetry_stats['좌우_대칭'] += 1
            if tb_symmetric:
                symmetry_stats['상하_대칭'] += 1
            if diag_symmetric:
                symmetry_stats['대각선_대칭'] += 1
            if not (lr_symmetric or tb_symmetric):
                symmetry_stats['비대칭'] += 1

        total = len(self.loader.numbers_df)
        print("\n대칭 패턴 출현 빈도:")
        for pattern, count in symmetry_stats.items():
            percentage = count / total * 100
            print(f"  {pattern}: {count}회 ({percentage:.1f}%)")

        return symmetry_stats

    def calculate_image_score(self, numbers):
        """
        번호 조합의 이미지 패턴 점수 계산

        Args:
            numbers: 번호 리스트 [n1, n2, n3, n4, n5, n6]

        Returns:
            점수 딕셔너리
        """
        positions = [self.number_to_position[num] for num in numbers]

        # 1. 시각적 밀도 점수 (적절한 거리 유지)
        distances = []
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                r1, c1 = positions[i]
                r2, c2 = positions[j]
                dist = np.sqrt((r2 - r1) ** 2 + (c2 - c1) ** 2)
                distances.append(dist)

        avg_distance = np.mean(distances)
        # 이상적 거리: 3.0~4.5 (너무 밀집되거나 분산되지 않음)
        if 3.0 <= avg_distance <= 4.5:
            density_score = 25
        elif 2.5 <= avg_distance <= 5.0:
            density_score = 15
        else:
            density_score = 5

        # 2. 4분면 균형 점수
        quadrants = {'Q1': 0, 'Q2': 0, 'Q3': 0, 'Q4': 0}
        for num in numbers:
            r, c = self.number_to_position[num]
            if r < 3.5 and c < 3.5:
                quadrants['Q1'] += 1
            elif r < 3.5 and c >= 3.5:
                quadrants['Q2'] += 1
            elif r >= 3.5 and c < 3.5:
                quadrants['Q3'] += 1
            else:
                quadrants['Q4'] += 1

        # 각 분면에 최소 1개씩 있으면 좋음
        quadrant_balance = sum(1 for v in quadrants.values() if v > 0)
        if quadrant_balance == 4:
            quadrant_score = 25  # 모든 분면에 분포
        elif quadrant_balance == 3:
            quadrant_score = 15
        else:
            quadrant_score = 5

        # 3. 무게중심 균형 점수
        center_row = np.mean([p[0] for p in positions])
        center_col = np.mean([p[1] for p in positions])
        ideal_row, ideal_col = 3, 3
        deviation = np.sqrt((center_row - ideal_row) ** 2 + (center_col - ideal_col) ** 2)

        if deviation < 1.0:
            balance_score = 25  # 중심에 가까움
        elif deviation < 1.5:
            balance_score = 15
        else:
            balance_score = 5

        # 4. 대칭성 점수
        left_count = sum(1 for r, c in positions if c < 3)
        right_count = sum(1 for r, c in positions if c > 3)
        lr_symmetric = abs(left_count - right_count) <= 1

        if lr_symmetric:
            symmetry_score = 25
        else:
            symmetry_score = 10

        total_score = density_score + quadrant_score + balance_score + symmetry_score

        return {
            'density_score': density_score,
            'quadrant_score': quadrant_score,
            'balance_score': balance_score,
            'symmetry_score': symmetry_score,
            'total_score': total_score,
            'avg_distance': avg_distance,
            'quadrants': quadrants,
            'center': (center_row, center_col),
            'deviation': deviation
        }

    def run_all(self):
        """모든 이미지 패턴 분석 실행"""
        print("\n" + "=" * 80)
        print("🎨 복권 용지 이미지 패턴 분석 시작")
        print("=" * 80)

        # 1. 시각적 밀도 분석
        density_df = self.analyze_visual_density()

        # 2. 4분면 패턴 분석
        quadrant_patterns = self.analyze_quadrant_patterns()

        # 3. 시각적 균형 분석
        balance_df = self.analyze_visual_balance()

        # 4. 대칭 패턴 분석
        symmetry_stats = self.analyze_symmetry_patterns()

        print("\n" + "=" * 80)
        print("✅ 이미지 패턴 분석 완료!")
        print("=" * 80)

        return {
            'density': density_df,
            'quadrant_patterns': quadrant_patterns,
            'balance': balance_df,
            'symmetry': symmetry_stats
        }


if __name__ == "__main__":
    from data_loader import LottoDataLoader

    # 데이터 로드
    data_path = "../Data/645_251227.csv"
    loader = LottoDataLoader(data_path)
    loader.load_data()
    loader.preprocess()
    loader.extract_numbers()

    # 분석 실행
    analyzer = ImagePatternAnalysis(loader)
    results = analyzer.run_all()

    # 테스트: 특정 번호 조합의 이미지 점수 계산
    print("\n" + "=" * 80)
    print("🧪 테스트: 번호 조합의 이미지 패턴 점수 계산")
    print("=" * 80)

    test_numbers = [7, 12, 19, 27, 33, 41]
    print(f"\n테스트 번호: {test_numbers}")

    score = analyzer.calculate_image_score(test_numbers)
    print(f"\n📊 이미지 패턴 점수:")
    print(f"  - 시각적 밀도 점수: {score['density_score']}점")
    print(f"  - 4분면 균형 점수: {score['quadrant_score']}점")
    print(f"  - 무게중심 균형 점수: {score['balance_score']}점")
    print(f"  - 대칭성 점수: {score['symmetry_score']}점")
    print(f"  - 총점: {score['total_score']}점 / 100점")
    print(f"\n상세 정보:")
    print(f"  - 평균 거리: {score['avg_distance']:.2f}")
    print(f"  - 4분면 분포: {score['quadrants']}")
    print(f"  - 무게중심: ({score['center'][0]:.2f}, {score['center'][1]:.2f})")
    print(f"  - 이상중심 편차: {score['deviation']:.2f}")
