"""
로또 복권 용지 그리드 패턴 분석
7x7 그리드 상에서 당첨번호의 공간적 분포 및 기하학적 패턴 분석
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter, defaultdict
from data_loader import LottoDataLoader
import os


class GridPatternAnalysis:
    """복권 용지 그리드 패턴 분석 클래스"""

    def __init__(self, loader):
        """
        Args:
            loader: LottoDataLoader 인스턴스
        """
        self.loader = loader
        self.rows = 7
        self.cols = 7

        # 번호를 그리드 좌표로 매핑 (1-45)
        self.number_to_position = {}
        number = 1
        for row in range(self.rows):
            for col in range(self.cols):
                if number <= 45:
                    self.number_to_position[number] = (row, col)
                    number += 1

        # 역매핑
        self.position_to_number = {v: k for k, v in self.number_to_position.items()}

        # 위치별 출현 빈도 초기화
        self.position_heatmap = np.zeros((self.rows, self.cols))
        self.zone_stats = defaultdict(int)

    def get_position(self, number):
        """번호의 그리드 좌표 반환"""
        return self.number_to_position.get(number, None)

    def get_zone(self, row, col):
        """그리드 위치의 구역 반환 (모서리, 가장자리, 중앙 등)"""
        # 모서리
        if (row, col) in [(0, 0), (0, 6), (6, 0), (6, 6)]:
            return "corner"
        # 가장자리
        elif row == 0 or row == 6 or col == 0 or col == 6:
            return "edge"
        # 중앙부
        elif 2 <= row <= 4 and 2 <= col <= 4:
            return "center"
        # 중간 영역
        else:
            return "middle"

    def analyze_position_frequency(self):
        """위치별 출현 빈도 분석"""
        print("\n" + "="*70)
        print("📍 그리드 위치별 출현 빈도 분석")
        print("="*70)

        # 모든 당첨번호의 위치 수집
        for _, row in self.loader.numbers_df.iterrows():
            winning_numbers = row['당첨번호']
            for num in winning_numbers:
                pos = self.get_position(num)
                if pos:
                    r, c = pos
                    self.position_heatmap[r, c] += 1

        # 위치별 통계 (45개 번호가 있는 위치만)
        # 빈 위치 제외하고 최소값 찾기
        valid_frequencies = []
        for pos, num in self.position_to_number.items():
            r, c = pos
            freq = self.position_heatmap[r, c]
            valid_frequencies.append((freq, pos, num))

        valid_frequencies.sort(reverse=True)

        max_freq, max_pos, max_number = valid_frequencies[0]
        min_freq, min_pos, min_number = valid_frequencies[-1]

        print(f"\n🔥 최다 출현 위치: Row {max_pos[0]}, Col {max_pos[1]} (번호 {max_number})")
        print(f"   출현 횟수: {int(max_freq)}회")

        print(f"\n❄️  최소 출현 위치: Row {min_pos[0]}, Col {min_pos[1]} (번호 {min_number})")
        print(f"   출현 횟수: {int(min_freq)}회")

        # 평균 출현 횟수
        avg_freq = np.mean(self.position_heatmap)
        print(f"\n📊 평균 출현 횟수: {avg_freq:.1f}회")

        return self.position_heatmap

    def analyze_zone_distribution(self):
        """구역별 분포 분석"""
        print("\n" + "="*70)
        print("🗺️  구역별 분포 분석")
        print("="*70)

        zone_counts = defaultdict(int)

        # 각 회차별로 구역 분석
        for _, row in self.loader.numbers_df.iterrows():
            winning_numbers = row['당첨번호']
            for num in winning_numbers:
                pos = self.get_position(num)
                if pos:
                    r, c = pos
                    zone = self.get_zone(r, c)
                    zone_counts[zone] += 1

        # 총 출현 횟수
        total = sum(zone_counts.values())

        # 결과 출력
        zone_names = {
            "corner": "모서리 (4칸)",
            "edge": "가장자리 (20칸)",
            "middle": "중간 (12칸)",
            "center": "중앙부 (9칸)"
        }

        print("\n구역별 출현 통계:")
        for zone in ["corner", "edge", "middle", "center"]:
            count = zone_counts[zone]
            pct = (count / total) * 100
            print(f"  {zone_names[zone]}: {count}회 ({pct:.2f}%)")

        return zone_counts

    def analyze_geometric_patterns(self):
        """기하학적 패턴 분석 (대각선, 가로, 세로 라인)"""
        print("\n" + "="*70)
        print("📐 기하학적 패턴 분석")
        print("="*70)

        pattern_stats = {
            "diagonal_main": [],      # 주 대각선 (0,0) -> (6,6)
            "diagonal_anti": [],      # 반대 대각선 (0,6) -> (6,0)
            "horizontal": defaultdict(list),  # 가로줄
            "vertical": defaultdict(list),    # 세로줄
        }

        # 각 회차 분석
        for idx, row in self.loader.numbers_df.iterrows():
            winning_numbers = row['당첨번호']
            positions = [self.get_position(num) for num in winning_numbers]

            diagonal_main_count = 0
            diagonal_anti_count = 0
            horizontal_counts = defaultdict(int)
            vertical_counts = defaultdict(int)

            for pos in positions:
                if pos:
                    r, c = pos

                    # 주 대각선
                    if r == c:
                        diagonal_main_count += 1

                    # 반대 대각선
                    if r + c == 6:
                        diagonal_anti_count += 1

                    # 가로/세로
                    horizontal_counts[r] += 1
                    vertical_counts[c] += 1

            pattern_stats["diagonal_main"].append(diagonal_main_count)
            pattern_stats["diagonal_anti"].append(diagonal_anti_count)

            # 같은 줄에 3개 이상 있는 경우
            for r, count in horizontal_counts.items():
                if count >= 3:
                    pattern_stats["horizontal"][count].append(row['회차'])

            for c, count in vertical_counts.items():
                if count >= 3:
                    pattern_stats["vertical"][count].append(row['회차'])

        # 대각선 통계
        main_diag_avg = np.mean(pattern_stats["diagonal_main"])
        anti_diag_avg = np.mean(pattern_stats["diagonal_anti"])

        print(f"\n📏 대각선 패턴:")
        print(f"  주 대각선 평균: {main_diag_avg:.2f}개/회차")
        print(f"  반대 대각선 평균: {anti_diag_avg:.2f}개/회차")

        # 같은 줄에 3개 이상 나온 경우
        print(f"\n📊 같은 가로줄에 3개 이상:")
        for count in sorted(pattern_stats["horizontal"].keys(), reverse=True):
            rounds = pattern_stats["horizontal"][count]
            print(f"  {count}개: {len(rounds)}회 발생")
            if len(rounds) <= 5:
                print(f"    회차: {rounds}")

        print(f"\n📊 같은 세로줄에 3개 이상:")
        for count in sorted(pattern_stats["vertical"].keys(), reverse=True):
            rounds = pattern_stats["vertical"][count]
            print(f"  {count}개: {len(rounds)}회 발생")
            if len(rounds) <= 5:
                print(f"    회차: {rounds}")

        return pattern_stats

    def analyze_spatial_clustering(self):
        """공간적 군집도 분석"""
        print("\n" + "="*70)
        print("🎯 공간적 군집도 분석")
        print("="*70)

        clustering_scores = []

        for idx, row in self.loader.numbers_df.iterrows():
            winning_numbers = row['당첨번호']
            positions = [self.get_position(num) for num in winning_numbers]

            # 위치 간 거리 계산 (맨해튼 거리)
            distances = []
            for i in range(len(positions)):
                for j in range(i+1, len(positions)):
                    if positions[i] and positions[j]:
                        r1, c1 = positions[i]
                        r2, c2 = positions[j]
                        dist = abs(r1 - r2) + abs(c1 - c2)
                        distances.append(dist)

            if distances:
                avg_distance = np.mean(distances)
                clustering_scores.append({
                    'round': row['회차'],
                    'avg_distance': avg_distance,
                    'min_distance': min(distances),
                    'max_distance': max(distances)
                })

        # 통계
        avg_distances = [s['avg_distance'] for s in clustering_scores]

        print(f"\n📏 평균 거리 통계:")
        print(f"  전체 평균: {np.mean(avg_distances):.2f}")
        print(f"  중앙값: {np.median(avg_distances):.2f}")
        print(f"  최소: {np.min(avg_distances):.2f}")
        print(f"  최대: {np.max(avg_distances):.2f}")

        # 가장 군집된 회차 (거리가 짧음)
        sorted_scores = sorted(clustering_scores, key=lambda x: x['avg_distance'])

        print(f"\n🔬 가장 군집된 회차 TOP 5:")
        for i, s in enumerate(sorted_scores[:5], 1):
            print(f"  {i}. {s['round']}회 - 평균거리: {s['avg_distance']:.2f}")

        print(f"\n🌌 가장 분산된 회차 TOP 5:")
        for i, s in enumerate(sorted_scores[-5:], 1):
            print(f"  {i}. {s['round']}회 - 평균거리: {s['avg_distance']:.2f}")

        return clustering_scores

    def plot_position_heatmap(self, output_dir="../output/charts"):
        """위치별 출현 빈도 히트맵"""
        os.makedirs(output_dir, exist_ok=True)

        fig, ax = plt.subplots(figsize=(12, 10))

        # 히트맵 그리기
        sns.heatmap(
            self.position_heatmap,
            annot=True,
            fmt='.0f',
            cmap='YlOrRd',
            cbar_kws={'label': '출현 횟수'},
            linewidths=0.5,
            ax=ax
        )

        # 각 셀에 번호 표시
        for row in range(self.rows):
            for col in range(self.cols):
                number = self.position_to_number.get((row, col))
                if number:
                    freq = int(self.position_heatmap[row, col])
                    ax.text(col + 0.5, row + 0.3, f'#{number}',
                           ha='center', va='center',
                           fontsize=8, color='blue', weight='bold')

        ax.set_title('로또 복권 용지 그리드 위치별 출현 빈도\n(번호: #1-#45, 빈도: 총 횟수)',
                     fontsize=14, weight='bold', pad=20)
        ax.set_xlabel('열 (Column)', fontsize=12)
        ax.set_ylabel('행 (Row)', fontsize=12)

        plt.tight_layout()
        output_path = os.path.join(output_dir, 'grid_position_heatmap.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✅ 히트맵 저장: {output_path}")

    def plot_zone_distribution(self, zone_counts, output_dir="../output/charts"):
        """구역별 분포 차트"""
        os.makedirs(output_dir, exist_ok=True)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # 파이 차트
        zone_names = {
            "corner": "모서리",
            "edge": "가장자리",
            "middle": "중간",
            "center": "중앙부"
        }

        labels = [zone_names[z] for z in zone_counts.keys()]
        sizes = list(zone_counts.values())
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']

        ax1.pie(sizes, labels=labels, autopct='%1.1f%%',
               colors=colors, startangle=90)
        ax1.set_title('구역별 출현 비율', fontsize=12, weight='bold')

        # 막대 그래프
        ax2.bar(labels, sizes, color=colors, alpha=0.7)
        ax2.set_ylabel('출현 횟수', fontsize=11)
        ax2.set_title('구역별 출현 횟수', fontsize=12, weight='bold')
        ax2.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        output_path = os.path.join(output_dir, 'grid_zone_distribution.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✅ 구역 분포 차트 저장: {output_path}")

    def plot_clustering_distribution(self, clustering_scores, output_dir="../output/charts"):
        """군집도 분포 차트"""
        os.makedirs(output_dir, exist_ok=True)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        avg_distances = [s['avg_distance'] for s in clustering_scores]
        rounds = [s['round'] for s in clustering_scores]

        # 히스토그램
        ax1.hist(avg_distances, bins=30, color='skyblue', edgecolor='black', alpha=0.7)
        ax1.axvline(np.mean(avg_distances), color='red', linestyle='--',
                   label=f'평균: {np.mean(avg_distances):.2f}')
        ax1.set_xlabel('평균 거리', fontsize=11)
        ax1.set_ylabel('빈도', fontsize=11)
        ax1.set_title('회차별 번호 간 평균 거리 분포', fontsize=12, weight='bold')
        ax1.legend()
        ax1.grid(alpha=0.3)

        # 시계열 (최근 200회)
        recent_scores = clustering_scores[-200:]
        recent_rounds = [s['round'] for s in recent_scores]
        recent_distances = [s['avg_distance'] for s in recent_scores]

        ax2.plot(recent_rounds, recent_distances, marker='o', markersize=3,
                linewidth=1, alpha=0.6)
        ax2.axhline(np.mean(avg_distances), color='red', linestyle='--',
                   label=f'전체 평균: {np.mean(avg_distances):.2f}')
        ax2.set_xlabel('회차', fontsize=11)
        ax2.set_ylabel('평균 거리', fontsize=11)
        ax2.set_title('최근 200회차 군집도 추이', fontsize=12, weight='bold')
        ax2.legend()
        ax2.grid(alpha=0.3)

        plt.tight_layout()
        output_path = os.path.join(output_dir, 'grid_clustering.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✅ 군집도 차트 저장: {output_path}")

    def run_all(self):
        """모든 그리드 패턴 분석 실행"""
        print("\n" + "="*70)
        print("🎨 로또 복권 용지 그리드 패턴 종합 분석")
        print("="*70)

        # 1. 위치별 빈도
        self.analyze_position_frequency()

        # 2. 구역별 분포
        zone_counts = self.analyze_zone_distribution()

        # 3. 기하학적 패턴
        self.analyze_geometric_patterns()

        # 4. 공간적 군집도
        clustering_scores = self.analyze_spatial_clustering()

        # 시각화
        print("\n" + "="*70)
        print("📊 차트 생성 중...")
        print("="*70)

        self.plot_position_heatmap()
        self.plot_zone_distribution(zone_counts)
        self.plot_clustering_distribution(clustering_scores)

        print("\n" + "="*70)
        print("✅ 그리드 패턴 분석 완료!")
        print("="*70)


if __name__ == "__main__":
    # 데이터 로드
    print("📊 데이터 로드 중...")
    data_path = "../Data/645_251227.csv"
    loader = LottoDataLoader(data_path)
    loader.load_data()
    loader.preprocess()
    loader.extract_numbers()

    # 그리드 패턴 분석
    analyzer = GridPatternAnalysis(loader)
    analyzer.run_all()
