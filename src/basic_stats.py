"""
기본 통계 분석 모듈
"""
import pandas as pd
import numpy as np
from collections import Counter


class BasicStats:
    """기본 통계 분석 클래스"""

    def __init__(self, data_loader):
        """
        Args:
            data_loader: LottoDataLoader 인스턴스
        """
        self.loader = data_loader
        self.df = data_loader.df
        self.numbers_df = data_loader.numbers_df

    def number_frequency(self, include_bonus=False):
        """번호별 출현 빈도 분석"""
        print("\n" + "="*60)
        print("1. 번호별 출현 빈도 분석")
        print("="*60)

        all_numbers = self.loader.get_all_numbers_flat(include_bonus=include_bonus)
        frequency = Counter(all_numbers)

        # DataFrame으로 변환
        freq_df = pd.DataFrame(
            sorted(frequency.items()),
            columns=['번호', '출현횟수']
        )

        total_draws = len(self.numbers_df)
        freq_df['출현율(%)'] = (freq_df['출현횟수'] / total_draws * 100).round(2)

        # 정렬
        freq_df = freq_df.sort_values('출현횟수', ascending=False).reset_index(drop=True)

        print(f"\n총 분석 회차: {total_draws}회")
        print(f"보너스 번호 포함: {'예' if include_bonus else '아니오'}\n")

        print("상위 10개 번호 (최다 출현):")
        print(freq_df.head(10).to_string(index=False))

        print("\n\n하위 10개 번호 (최소 출현):")
        print(freq_df.tail(10).to_string(index=False))

        return freq_df

    def section_analysis(self):
        """구간별 분석 (저/중/고)"""
        print("\n" + "="*60)
        print("2. 구간별 출현 분석")
        print("="*60)

        all_numbers = self.loader.get_all_numbers_flat(include_bonus=False)

        low = [n for n in all_numbers if 1 <= n <= 15]
        mid = [n for n in all_numbers if 16 <= n <= 30]
        high = [n for n in all_numbers if 31 <= n <= 45]

        total = len(all_numbers)

        section_stats = pd.DataFrame({
            '구간': ['저구간 (1-15)', '중구간 (16-30)', '고구간 (31-45)'],
            '출현횟수': [len(low), len(mid), len(high)],
            '비율(%)': [
                round(len(low) / total * 100, 2),
                round(len(mid) / total * 100, 2),
                round(len(high) / total * 100, 2)
            ]
        })

        print("\n" + section_stats.to_string(index=False))

        return section_stats

    def odd_even_analysis(self):
        """홀수/짝수 분석"""
        print("\n" + "="*60)
        print("3. 홀수/짝수 분석")
        print("="*60)

        all_numbers = self.loader.get_all_numbers_flat(include_bonus=False)

        odd = [n for n in all_numbers if n % 2 == 1]
        even = [n for n in all_numbers if n % 2 == 0]

        total = len(all_numbers)

        odd_even_stats = pd.DataFrame({
            '구분': ['홀수', '짝수'],
            '출현횟수': [len(odd), len(even)],
            '비율(%)': [
                round(len(odd) / total * 100, 2),
                round(len(even) / total * 100, 2)
            ]
        })

        print("\n" + odd_even_stats.to_string(index=False))

        # 회차별 홀짝 분포
        print("\n\n회차별 홀짝 개수 분포:")
        odd_counts = []

        for _, row in self.numbers_df.iterrows():
            nums = row['당첨번호']
            odd_count = sum(1 for n in nums if n % 2 == 1)
            odd_counts.append(odd_count)

        odd_count_dist = Counter(odd_counts)
        odd_dist_df = pd.DataFrame(
            sorted(odd_count_dist.items()),
            columns=['홀수개수', '회차수']
        )

        print(odd_dist_df.to_string(index=False))

        return odd_even_stats, odd_dist_df

    def consecutive_analysis(self):
        """연속 번호 분석"""
        print("\n" + "="*60)
        print("4. 연속 번호 출현 분석")
        print("="*60)

        consecutive_counts = []

        for _, row in self.numbers_df.iterrows():
            nums = sorted(row['당첨번호'])
            consecutive = 0

            for i in range(len(nums) - 1):
                if nums[i+1] - nums[i] == 1:
                    consecutive += 1

            consecutive_counts.append(consecutive)

        consec_dist = Counter(consecutive_counts)
        consec_df = pd.DataFrame(
            sorted(consec_dist.items()),
            columns=['연속번호쌍', '회차수']
        )

        consec_df['비율(%)'] = (consec_df['회차수'] / len(self.numbers_df) * 100).round(2)

        print("\n" + consec_df.to_string(index=False))

        return consec_df

    def sum_analysis(self):
        """당첨번호 합계 분석"""
        print("\n" + "="*60)
        print("5. 당첨번호 합계 분석")
        print("="*60)

        sums = []

        for _, row in self.numbers_df.iterrows():
            total = sum(row['당첨번호'])
            sums.append(total)

        sum_stats = {
            '평균': round(np.mean(sums), 2),
            '중앙값': round(np.median(sums), 2),
            '최소값': min(sums),
            '최대값': max(sums),
            '표준편차': round(np.std(sums), 2)
        }

        sum_df = pd.DataFrame([sum_stats])

        print("\n" + sum_df.to_string(index=False))

        # 합계 구간별 분포
        print("\n\n합계 구간별 분포:")
        bins = [0, 100, 120, 140, 160, 180, 200, 300]
        labels = ['~100', '101-120', '121-140', '141-160', '161-180', '181-200', '201~']

        sum_bins = pd.cut(sums, bins=bins, labels=labels)
        sum_dist = sum_bins.value_counts().sort_index()

        sum_dist_df = pd.DataFrame({
            '합계구간': sum_dist.index,
            '회차수': sum_dist.values,
            '비율(%)': (sum_dist.values / len(sums) * 100).round(2)
        })

        print(sum_dist_df.to_string(index=False))

        return sum_df, sum_dist_df

    def run_all(self):
        """모든 기본 통계 분석 실행"""
        print("\n\n" + "🎲 "*20)
        print("기본 통계 분석 시작")
        print("🎲 "*20 + "\n")

        freq_df = self.number_frequency(include_bonus=False)
        section_stats = self.section_analysis()
        odd_even_stats, odd_dist = self.odd_even_analysis()
        consec_df = self.consecutive_analysis()
        sum_stats, sum_dist = self.sum_analysis()

        print("\n\n" + "✅ "*20)
        print("기본 통계 분석 완료")
        print("✅ "*20 + "\n")

        return {
            'frequency': freq_df,
            'section': section_stats,
            'odd_even': odd_even_stats,
            'odd_distribution': odd_dist,
            'consecutive': consec_df,
            'sum_stats': sum_stats,
            'sum_distribution': sum_dist
        }
