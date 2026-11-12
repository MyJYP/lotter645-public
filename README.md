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

## 재미로 보는 번호 차트

**데이터 탐색 → 재미로 보는 번호 차트**에서 세 화면을 이용할 수 있습니다.

- **출현 흐름** — 번호별 5·10·20·60·120회 출현률, 교차와 선의 상태, 실제 출현 회차를 비교합니다. 표 왼쪽 체크박스로 관심 번호를 바꿀 수 있습니다.
- **당첨금 배분** — 1등 총액 또는 게임당 금액을 본번호 6개에 균등 배분한 누계·평균을 살펴봅니다. 비교 번호는 최대 6개이며 전체·최근 120회·60회로 조회합니다.
- **보너스 번호** — 보너스 출현·간격·본번호 비교, 관측 가능한 다음 회차 기록, 해당 회차의 2등 금액을 확인합니다.

자료 부족·미관측 회차·금액 제외 사유를 표시합니다. 출현률은 과거 관측 비율이며 금액은 분석용 배분값입니다. 동일 확률 안내와 동행복권·키움증권·Fidelity 출처를 화면 하단에서 확인할 수 있습니다.

기능 명세는 [기획서](docs/NUMBER_TREND_PLAN.md), [설계](docs/NUMBER_TREND_DESIGN.md), [작업 목록](docs/NUMBER_TREND_TASKS.md), [태스크별 리뷰](docs/reviews/README.md)에 있습니다. [독립 HTML 시안](docs/previews/number-trend.html)은 최초 화면 검토 자료입니다.
