# 로또 6/45 분석 및 번호 추천

과거 당첨 번호의 분포를 탐색하고 사용자 패턴 선호도 점수에 따라 6개 번호를 추출하는 Streamlit 앱입니다. 패턴 점수는 입력한 선호 조건과의 일치 정도를 나타냅니다. 각 조합의 수학적 당첨 확률은 같습니다.

## 실행

Python 3.14를 사용합니다.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run src/web_app.py
```

번호 추천의 저장 이력은 현재 브라우저 세션에서만 볼 수 있습니다. 당첨 데이터는 `Data/645_251227.csv`의 배포본을 읽습니다. 검증된 새 회차는 저장소에서 CSV를 갱신하여 반영합니다.

당첨 번호와 등수별 당첨게임 수·1게임당 당첨금은 동행복권 추첨 결과를 기준으로 확인합니다. [동행복권 로또 6/45 추첨 결과](https://www.dhlottery.co.kr/lt645/result)

## Streamlit Community Cloud

이 저장소의 `main` 브랜치, `src/web_app.py`를 선택하고 Advanced settings에서 Python 3.14를 선택합니다. 프리미엄 기능을 사용하려면 Streamlit Secrets에 `[premium]` 섹션을 만들고 `access_codes`에 새로 생성한 충분히 긴 무작위 코드의 목록을 지정합니다. 설정이 비어 있으면 공개 분석과 번호 추출만 제공됩니다.

## 테스트

```sh
python -m pip install pytest==9.2.0
python -m pytest -q tests
```

추출 조건과 점수 계산 방식은 [패턴 선호도 설명](docs/PATTERN_PREFERENCE.md)에서 확인할 수 있습니다.
