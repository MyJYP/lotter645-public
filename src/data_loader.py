"""
로또 645 데이터 로더 및 전처리 모듈
"""
import pandas as pd
import numpy as np
from pathlib import Path


def normalize_draw_history(frame):
    """Validate observed draws and return a copy ordered newest first."""
    result = frame.copy()
    rounds = pd.to_numeric(result['회차'], errors='coerce')
    if rounds.isna().any() or not np.isfinite(rounds).all() or (rounds <= 0).any() or (rounds % 1 != 0).any():
        raise ValueError('회차는 양의 정수여야 합니다.')
    if rounds.duplicated().any():
        raise ValueError('중복 회차가 있습니다.')
    result['회차'] = rounds.astype(int)
    if '당첨번호' in result:
        for numbers in result['당첨번호']:
            if (len(numbers) != 6 or len(set(numbers)) != 6 or
                    any(isinstance(n, (bool, np.bool_)) or not isinstance(n, (int, np.integer)) or not 1 <= n <= 45 for n in numbers)):
                raise ValueError('본번호는 1~45의 서로 다른 정수 6개여야 합니다.')
    return result.sort_values('회차', ascending=False).reset_index(drop=True)


class LottoDataLoader:
    """로또 데이터를 로드하고 전처리하는 클래스"""

    def __init__(self, data_path):
        """
        Args:
            data_path: CSV 파일 경로
        """
        self.data_path = Path(data_path)
        self.df = None
        self.numbers_df = None

    def load_data(self):
        """CSV 데이터 로드"""
        print(f"데이터 로딩 중: {self.data_path}")

        # CSV 파일 읽기 (인코딩 처리)
        # 첫 번째 행은 깨진 헤더이므로 건너뛰고, 두 번째 행을 헤더로 사용
        try:
            self.df = pd.read_csv(self.data_path, encoding='utf-8-sig', skiprows=1)
        except UnicodeDecodeError:
            self.df = pd.read_csv(self.data_path, encoding='cp949', skiprows=1)

        print(f"✓ 데이터 로드 완료: {len(self.df)}개 회차")
        return self.df

    def preprocess(self):
        """데이터 전처리"""
        print("\n데이터 전처리 중...")

        # 숫자 컬럼에서 쉼표 제거 및 숫자 변환
        numeric_columns = [
            '1등 당첨자수', '1등 당첨액', '2등 당첨자수', '2등 당첨액',
            '3등 당첨자수', '3등 당첨액', '4등 당첨자수', '4등 당첨액',
            '5등 당첨자수', '5등 당첨액'
        ]

        for col in numeric_columns:
            if col in self.df.columns:
                self.df[col] = self.df[col].astype(str).str.replace(',', '').astype(float)

        # 회차 숫자로 변환
        self.df['회차'] = pd.to_numeric(self.df['회차'], errors='coerce')

        # 날짜 변환
        self.df['일자'] = pd.to_datetime(self.df['일자'], errors='coerce')

        # 결측치 제거
        self.df = self.df.dropna(subset=['회차'])
        self.df = normalize_draw_history(self.df)

        print(f"✓ 전처리 완료")
        return self.df

    def extract_numbers(self):
        """당첨번호 추출하여 별도 데이터프레임 생성"""
        print("당첨번호 추출 중...")

        numbers_data = []

        for idx, row in self.df.iterrows():
            round_num = row['회차']
            date = row['일자']

            # 당첨번호 6개
            winning_numbers = [
                int(row['당첨번호#1']),
                int(row['당첨번호#2']),
                int(row['당첨번호#3']),
                int(row['당첨번호#4']),
                int(row['당첨번호#5']),
                int(row['당첨번호#6'])
            ]

            # 보너스 번호
            bonus_number = int(row['당첨번호#7'])

            numbers_data.append({
                '회차': round_num,
                '일자': date,
                '당첨번호': sorted(winning_numbers),
                '보너스번호': bonus_number,
                '번호1': winning_numbers[0],
                '번호2': winning_numbers[1],
                '번호3': winning_numbers[2],
                '번호4': winning_numbers[3],
                '번호5': winning_numbers[4],
                '번호6': winning_numbers[5],
            })

        self.numbers_df = normalize_draw_history(pd.DataFrame(numbers_data, columns=[
            '회차', '일자', '당첨번호', '보너스번호',
            '번호1', '번호2', '번호3', '번호4', '번호5', '번호6',
        ]))
        print(f"✓ 당첨번호 추출 완료")
        return self.numbers_df

    def get_all_numbers_flat(self, include_bonus=False):
        """모든 당첨번호를 1차원 리스트로 반환"""
        all_numbers = []

        for _, row in self.numbers_df.iterrows():
            all_numbers.extend(row['당첨번호'])
            if include_bonus:
                all_numbers.append(row['보너스번호'])

        return all_numbers

    def load_data_until_round(self, max_round):
        """특정 회차까지만 데이터 로드 (백테스팅용)

        Args:
            max_round: 최대 회차 번호 (포함)

        Returns:
            LottoDataLoader: self (메서드 체이닝)
        """
        self.load_data()
        self.preprocess()

        # 회차 필터링 (max_round 포함)
        self.df = self.df[self.df['회차'] <= max_round].copy()

        self.extract_numbers()
        return self

    def get_round_data(self, round_num):
        """특정 회차의 당첨번호 반환

        Args:
            round_num: 회차 번호

        Returns:
            list or None: 당첨번호 6개 (정렬)
        """
        if self.numbers_df is None:
            return None

        row = self.numbers_df[self.numbers_df['회차'] == round_num]
        if row.empty:
            return None
        return sorted(row.iloc[0]['당첨번호'])

    def get_summary(self):
        """데이터 요약 정보 출력"""
        print("\n" + "="*60)
        print("로또 645 데이터 요약")
        print("="*60)
        print(f"총 회차 수: {len(self.df)}회")
        print(f"기간: {self.df['일자'].min().strftime('%Y.%m.%d')} ~ {self.df['일자'].max().strftime('%Y.%m.%d')}")
        print(f"회차 범위: {int(self.df['회차'].min())}회 ~ {int(self.df['회차'].max())}회")
        print("="*60 + "\n")


def main():
    """테스트용 메인 함수"""
    data_path = "../Data/645_251227.csv"

    loader = LottoDataLoader(data_path)
    loader.load_data()
    loader.preprocess()
    loader.extract_numbers()
    loader.get_summary()

    print("샘플 데이터 (최근 5회차):")
    print(loader.numbers_df.head())


if __name__ == "__main__":
    main()
