# MAC23_Lect 코드리뷰 인계

최신 요청은 T06 P2 수정 재리뷰와 T07·T08 개발 리뷰다. 현재 로컬 v6.2.15, T01~T08 구현 완료이며 남은 범위는 T09~T18이다. 기준 커밋은 `70a4ceabf665f81d3e7a46e856dd435caffda67a`이고 변경은 미커밋 상태다.

변경 파일은 `src/time_series.py`, `tests/test_number_trends.py`, `VERSION`과 관련 문서다. T06은 원본 필드별 오류 사유가 최종 사유에서 유실되는 P2를 재현·수정했다. 관련 테스트 141개 통과. T07·T08은 실제 전체·최근 120회·최근 60회, 두 금액 기준으로 누계·평균 270건과 합계 보존을 검산했다. 알려진 수정 대기 결함은 현재 개발 검증에서 추가 발견되지 않았으며 통계·UI·전체 통합 검증은 후속 범위다.

리뷰 대상과 검증 결과는 [T06](reviews/T06.md), [T07](reviews/T07.md), [T08](reviews/T08.md)에 기록했다. 인계 문서를 기준으로 리뷰하고 결과를 MAC21-Vcoding에 전달해 주세요. 각 결과는 해당 태스크 리뷰 파일에 남겨 주세요. 아래 내용은 이전 인계 이력이다.

## 대상과 완료 범위

프로젝트는 이 문서가 속한 `lotter645-public` 저장소다. 완료 태스크는 **T01 회차·본번호·보너스 검증**, **T02 금액·게임 수 검증 및 회차 결합**이다. 전체 18개 중 2개 완료했으며 T03~T18이 남아 있다.

T03은 빈 입력·자료 범위와 반환 컬럼 확정, T04~T11은 이동평균·교차·당첨금 배분·보너스 계산, T12~T15는 Streamlit 화면 연결, T16~T18은 통합 검증·버전·배포다. 기준 명세는 [핵심 설계](NUMBER_TREND_DESIGN.md), 완료 조건은 [작업 목록](NUMBER_TREND_TASKS.md)에서 확인한다.

## 기준 커밋과 미커밋 변경

기준 커밋은 `70a4ceabf665f81d3e7a46e856dd435caffda67a`다. 해당 커밋의 버전은 v6.2.5이고 현재 로컬 버전은 v6.2.7이다. 아래 변경은 현재 작업 트리에 있다.

| 상태 | 파일 | 내용 |
|---|---|---|
| 수정 | `src/time_series.py` | T01 `validate_trend_numbers()`, T02 `_parse_prize_integer()`·`prepare_trend_data()` 추가 |
| 신규 | `tests/test_number_trends.py` | T01·T02 직접 검증 사례 |
| 수정 | `VERSION` | 소스 수정별 패치 증가를 반영한 v6.2.7 |
| 수정 | `README.md` | 기획서와 미리보기 링크 |
| 신규 | `docs/NUMBER_TREND_PLAN.md` | 기획서 |
| 신규 | `docs/NUMBER_TREND_DESIGN.md` | 구현 설계 |
| 신규 | `docs/NUMBER_TREND_TASKS.md` | 태스크·의존 관계·완료 기록 |
| 신규 | `docs/NUMBER_TREND_T01_USAGE.md` | T01 토큰 측정 |
| 신규 | `docs/NUMBER_TREND_REVIEW_HANDOFF.md` | 이 인계 문서 |
| 신규 | `docs/previews/number-trend.html` | 실제 보유 데이터의 독립 HTML 시안 |
| 신규 | `docs/previews/number-trend-desktop.png`, `number-trend-mobile.png` | 시안 캡처 |

리뷰 시 `git diff 70a4ceabf665f81d3e7a46e856dd435caffda67a -- src/time_series.py VERSION README.md`로 추적 파일 변경을 확인한다. 신규 파일은 `git status --short`와 실제 파일을 읽어 확인한다.

## 실행한 검증과 결과

저장소 루트에서 다음 명령을 실행했다.

```sh
/tmp/lotter645-public-venv/bin/python -m pytest -q tests/test_number_trends.py tests/test_pattern_features.py
```

T01 완료 시 24개 통과, T02 추가 후 **40개 통과**했다. 번호 정렬·중복·잘못된 번호·결측 보너스, 회차 결합, `9007199254740993` 원 정밀도, 금액·게임 수 이상값과 제외 사유를 확인한다.

실제 데이터 검증에서는 `LottoDataLoader`로 배포 CSV를 읽고 `prepare_trend_data(loader.numbers_df, loader.df)`를 실행했다. **601~1249회 649건**, 네 금액·게임 수 컬럼의 Python 정수 보존, 정상 입력의 제외 사유 공백을 확인했다. `git diff --check`도 통과했다.

별도 HTML 시안은 이전 작업에서 브라우저로 번호·기간·선 선택·툴팁·45개 번호 표를 확인했고 모바일 가로 넘침과 JavaScript 오류가 없었다. T01·T02의 실제 앱 UI 연결은 T12 이후 범위다. 전체 회귀와 운영 확인은 T16~T18에서 수행한다.

## 알려진 문제와 리뷰 확인점

- 입력 금액이 호출 전에 float로 변환되어 이미 정밀도를 잃었으면 원래 값을 복구할 수 없다. T02는 전달받은 정수·문자열의 정밀도를 유지하며 현재 실제 CSV 금액은 직접 검증을 통과했다.
- 빈 입력·누락 회차·최종 반환 컬럼 정리는 T03의 남은 범위다. 현재 입력 계약과 실제 동작의 차이를 발견하면 사례를 남긴다.
- 재사용한 `normalize_draw_history()`의 입력 처리와 새 보너스 검증 사이에서 예외 유형·변환이 불일치하는지 확인한다.
- 금액 제외 사유는 현재 필드별로 반환한다. 0게임의 금액 제외 사유를 실제 배분에서 어떻게 적용할지는 T06의 규칙으로 처리한다.

확인점은 리뷰 후보이며, 재현한 결함은 리뷰 결과에서 별도로 명시한다.

## 리뷰와 회신 요청

**인계 문서를 기준으로 리뷰하고 결과를 MAC21-Vcoding에 전달해 주세요.** T01·T02의 오류·회귀·설계 불일치를 우선 확인하고 심각도, 파일·라인, 재현 입력, 수정 제안을 `docs/NUMBER_TREND_T01_REVIEW.md`에 기록해 주세요. 같은 작업 트리이므로 코드 수정은 원 개발 세션에서 반영합니다.

리뷰 수신 MAC23_Lect 스레드는 `01a1c7ee-5c7a-7261-acd3-3e1ca1320aa8`이다. 회신할 MAC21-Vcoding 스레드는 `01a1ba4d-dbe2-7f33-9b7e-ce9d73cb5ddb`이다. 스레드 전송이 실패하면 리뷰 결과 파일에 회신 실패 사유도 기록한다.

## 전달 상태

기존 두 차례 요청은 `already has an active writer` 오류로 거부됐다. 이 문서를 보완한 뒤 지정 스레드로 다시 전송한다. 최종 전송 결과는 아래에 기록한다.

문서 보완 후 재전송도 `thread/resume failed: already has an active writer (code -32600)`로 거부됐다. 요청 메시지는 전달 전이며, MAC23_Lect 세션의 실행기 점유가 해제되어야 같은 전송 도구로 재시도할 수 있다.


## 리뷰 확인 완료

MAC21-Vcoding에서 MAC23_Lect의 완료된 리뷰 턴을 조회했다. T01·T02 수정 필요 사항 없음, 관련 테스트 40개 및 실제 649회차·경계값 48건·빈 입력 2건 검산 통과를 확인했다. 결과를 [T01·T02 리뷰 기록](NUMBER_TREND_T01_REVIEW.md)에 보관했다. 자동 전송 실패 이후 MAC23_Lect에서 사용자 요청으로 리뷰가 수행됐으며, 이 확인으로 결과를 원 개발 세션에 반영했다.


## T03 추가 인계 (2026-11-11)

MAC23_Lect에서 사용자 요청으로 T03을 구현했다. 검토 대상은 `prepare_trend_data()`의 고정 스키마·빈 입력·날짜 처리, 신규 `summarize_trend_coverage()` 및 추가 경계 테스트다. 설계 문서에 반환 계약과 범위 요약 필드를 명시했다. 로컬 버전은 v6.2.8이다.

- 관련 테스트: `PYTHONDONTWRITEBYTECODE=1 /tmp/lotter645-public-venv/bin/python -m pytest -q -p no:cacheprovider tests/test_number_trends.py tests/test_pattern_features.py` → 49개 통과.
- 실제 CSV: 601~1249회 649건, 누락 0건, 결측 보너스 0건, 마지막 날짜 2026-11-07. 금액 Python 정수 보존 확인.
- 빈 입력은 같은 스키마, 날짜 미상은 NaT, 누락 회차는 관측 행에 추가하지 않음. T04에서 정수 회차 인덱스로 재색인해야 함.
- 다음 태스크: T04. 총 3/18개 완료. 커밋·푸시·배포 미수행.


## T04 추가 인계 (2026-11-11)

사용자 요청으로 `src/time_series.py`의 `build_appearance()`와 관련 테스트를 추가했다. 검토 범위는 본번호·보너스 출현 행렬과 5·10·20·60·120회 횟수·출현률이다. `cross`와 표시 범위 처리는 T05에서 구현한다.

관련 테스트 69개 통과. 실제 649회차에서 모드별 29,205행, 모드별 675건의 직접 집계 대조 통과. 세부 경계·불변성 검증은 작업 목록 T04 실행 기록에 정리했다. 로컬 버전 v6.2.9, 총 4/18개 완료, 다음 T05. 커밋·푸시·배포 미수행.


T05·T06 구현 후 지정 MAC23_Lect 스레드로 재요청했으나 `already has an active writer (code -32600)`로 거부됐다. 최신 요청의 자동 전송은 대기 상태이며 태스크별 문서에 리뷰 자료를 준비했다.


최신 T06 수정·T07·T08 리뷰 요청도 지정 스레드의 `already has an active writer (code -32600)` 오류로 거부됐다. 요청 문서와 태스크별 리뷰 자료는 준비되어 있으며 자동 전송은 대기 상태다.
