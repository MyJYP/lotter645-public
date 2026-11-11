from pathlib import Path

from streamlit.testing.v1 import AppTest

from session_history import SessionHistory

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "Data/645_251227.csv"
TEST_CODE = "synthetic-code-for-auth-tests"


def test_premium_authentication_does_not_disclose_codes_and_checks_revocation(monkeypatch):
    monkeypatch.setenv("LOTTO_DEV_MODE", "true")
    app = AppTest.from_file(str(ROOT / "src/web_app.py"), default_timeout=60)
    app.secrets["premium"] = {"access_codes": [TEST_CODE]}
    app.run()
    app.sidebar.radio[0].set_value("🔬 백테스팅 결과").run()
    assert not app.exception
    assert "🔄 데이터 업데이트" not in app.sidebar.radio[0].options
    assert not any(button.key == "start_backtest_3" for button in app.button)

    app.text_input(key="premium_code_input").set_value("invalid-code")
    next(button for button in app.button if button.label == "잠금 해제").click().run()
    assert not app.exception
    for element in [*app.markdown, *app.text, *app.error, *app.info, *app.warning]:
        assert TEST_CODE not in element.value
        assert "invalid-code" not in element.value

    app.session_state["premium_retry_at"] = 0
    app.text_input(key="premium_code_input").set_value(TEST_CODE)
    next(button for button in app.button if button.label == "잠금 해제").click().run()
    assert not app.exception
    assert any(button.key == "start_backtest_3" for button in app.button)
    assert "premium_code_input" not in app.session_state

    app.secrets["premium"] = {"access_codes": []}
    app.run()
    assert not app.exception
    assert not any(button.key == "start_backtest_3" for button in app.button)
    assert "premium_digest" not in app.session_state


def test_public_recommendation_history_is_session_local():
    before = CSV.read_bytes()
    first = AppTest.from_file(str(ROOT / "src/web_app.py"), default_timeout=60).run()
    second = AppTest.from_file(str(ROOT / "src/web_app.py"), default_timeout=60).run()
    for app in (first, second):
        app.sidebar.radio[0].set_value("🎯 번호 추천").run()
        app.radio(key="recommendation_mode").set_value("기존 전략 (보조)").run()
        assert not app.exception

    history_a = SessionHistory(first.session_state["fixed_mode_history"])
    history_b = SessionHistory(second.session_state["fixed_mode_history"])
    history_a.save_history(1, "test", [1, 2, 3, 4, 5, 6])
    first.run()
    second.run()
    assert any(button.key == "delete_latest_history" for button in first.button)
    assert not any(button.key == "delete_latest_history" for button in second.button)
    assert not history_b.delete_history(0)
    first.button(key="delete_latest_history").click().run()
    assert history_a.load_history().empty
    assert CSV.read_bytes() == before
