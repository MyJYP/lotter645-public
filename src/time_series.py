"""
시계열 분석 모듈
"""
import pandas as pd
import numpy as np
from collections import Counter, defaultdict


class TimeSeriesAnalysis:
    """시계열 분석 클래스"""

    def __init__(self, data_loader):
        """
        Args:
            data_loader: LottoDataLoader 인스턴스
        """
        self.loader = data_loader
        self.df = data_loader.df
        self.numbers_df = data_loader.numbers_df

    def recent_hot_cold_numbers(self, recent_rounds=50, top_n=10):
        """최근 핫넘버/콜드넘버 분석"""
        print("\n" + "="*60)
        print(f"1. 최근 {recent_rounds}회차 핫넘버/콜드넘버 분석")
        print("="*60)

        # 최근 N회차 데이터
        recent_data = self.numbers_df.head(recent_rounds)

        all_numbers = []
        for _, row in recent_data.iterrows():
            all_numbers.extend(row['당첨번호'])

        frequency = Counter(all_numbers)

        # 모든 번호(1-45) 초기화
        all_45_numbers = {i: 0 for i in range(1, 46)}
        all_45_numbers.update(frequency)

        freq_df = pd.DataFrame(
            sorted(all_45_numbers.items(), key=lambda x: x[1], reverse=True),
            columns=['번호', '출현횟수']
        )

        freq_df['출현율(%)'] = (freq_df['출현횟수'] / recent_rounds * 100).round(2)

        print(f"\n🔥 핫넘버 TOP {top_n} (최다 출현):")
        print(freq_df.head(top_n).to_string(index=False))

        print(f"\n❄️  콜드넘버 TOP {top_n} (최소 출현):")
        print(freq_df.tail(top_n).to_string(index=False))

        return freq_df

    def number_appearance_interval(self, number):
        """특정 번호의 출현 간격 분석"""
        print("\n" + "="*60)
        print(f"2. 번호 {number}의 출현 간격 분석")
        print("="*60)

        appearance_rounds = []

        for idx, row in self.numbers_df.iterrows():
            if number in row['당첨번호'] or number == row['보너스번호']:
                appearance_rounds.append(row['회차'])

        if not appearance_rounds:
            print(f"\n번호 {number}는 출현 기록이 없습니다.")
            return None

        # 출현 간격 계산
        intervals = []
        for i in range(len(appearance_rounds) - 1):
            interval = appearance_rounds[i] - appearance_rounds[i+1]
            intervals.append(interval)

        if intervals:
            interval_stats = {
                '총 출현 횟수': len(appearance_rounds),
                '평균 간격': round(np.mean(intervals), 2),
                '최소 간격': min(intervals),
                '최대 간격': max(intervals),
                '표준편차': round(np.std(intervals), 2) if len(intervals) > 1 else 0
            }

            stats_df = pd.DataFrame([interval_stats])
            print("\n" + stats_df.to_string(index=False))

            # 최근 출현 정보
            latest_round = appearance_rounds[0]
            current_round = self.numbers_df.iloc[0]['회차']
            rounds_since = int(current_round - latest_round)

            print(f"\n최근 출현: {latest_round}회차")
            print(f"미출현 기간: {rounds_since}회")

            return stats_df, appearance_rounds
        else:
            print(f"\n번호 {number}는 1회만 출현했습니다.")
            return None

    def long_missing_numbers(self, top_n=10):
        """장기 미출현 번호 분석"""
        print("\n" + "="*60)
        print(f"3. 장기 미출현 번호 TOP {top_n}")
        print("="*60)

        current_round = self.numbers_df.iloc[0]['회차']
        last_appearance = {}

        # 모든 번호의 최근 출현 회차 찾기
        for num in range(1, 46):
            for idx, row in self.numbers_df.iterrows():
                if num in row['당첨번호'] or num == row['보너스번호']:
                    last_appearance[num] = row['회차']
                    break

            # 한 번도 출현하지 않은 경우
            if num not in last_appearance:
                last_appearance[num] = 0

        # 미출현 기간 계산
        missing_periods = {
            num: int(current_round - last_round)
            for num, last_round in last_appearance.items()
        }

        # 정렬
        sorted_missing = sorted(
            missing_periods.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]

        missing_df = pd.DataFrame(
            sorted_missing,
            columns=['번호', '미출현회차']
        )

        missing_df['최근출현'] = missing_df['번호'].map(last_appearance)

        print("\n" + missing_df.to_string(index=False))

        return missing_df

    def rolling_frequency(self, window_size=100):
        """이동 평균 빈도 분석 (특정 번호들의 트렌드)"""
        print("\n" + "="*60)
        print(f"4. 이동 평균 빈도 분석 (윈도우: {window_size}회)")
        print("="*60)

        # 번호별 이동 평균 계산
        number_trends = defaultdict(list)

        total_rounds = len(self.numbers_df)

        for i in range(0, total_rounds - window_size + 1, 10):  # 10회차씩 이동
            window_data = self.numbers_df.iloc[i:i+window_size]

            all_numbers = []
            for _, row in window_data.iterrows():
                all_numbers.extend(row['당첨번호'])

            frequency = Counter(all_numbers)

            for num in range(1, 46):
                number_trends[num].append(frequency.get(num, 0))

        # 최근 트렌드 상승 번호 찾기
        trend_changes = {}
        for num, trends in number_trends.items():
            if len(trends) >= 2:
                recent_avg = np.mean(trends[:3]) if len(trends) >= 3 else trends[0]
                old_avg = np.mean(trends[-3:]) if len(trends) >= 3 else trends[-1]
                trend_changes[num] = recent_avg - old_avg

        # 상승세 TOP 10
        rising = sorted(
            trend_changes.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        rising_df = pd.DataFrame(
            rising,
            columns=['번호', '트렌드변화']
        )

        print("\n📈 상승세 번호 TOP 10:")
        print(rising_df.to_string(index=False))

        # 하락세 TOP 10
        falling = sorted(
            trend_changes.items(),
            key=lambda x: x[1]
        )[:10]

        falling_df = pd.DataFrame(
            falling,
            columns=['번호', '트렌드변화']
        )

        print("\n📉 하락세 번호 TOP 10:")
        print(falling_df.to_string(index=False))

        return rising_df, falling_df

    def run_all(self):
        """모든 시계열 분석 실행"""
        print("\n\n" + "📊 "*20)
        print("시계열 분석 시작")
        print("📊 "*20 + "\n")

        hot_cold_50 = self.recent_hot_cold_numbers(recent_rounds=50)
        hot_cold_100 = self.recent_hot_cold_numbers(recent_rounds=100)
        missing = self.long_missing_numbers(top_n=10)
        rising, falling = self.rolling_frequency(window_size=100)

        print("\n\n" + "✅ "*20)
        print("시계열 분석 완료")
        print("✅ "*20 + "\n")

        return {
            'hot_cold_50': hot_cold_50,
            'hot_cold_100': hot_cold_100,
            'missing_numbers': missing,
            'rising_trend': rising,
            'falling_trend': falling
        }
