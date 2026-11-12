from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = f'''
import sys
sys.path.insert(0, {str(ROOT / 'src')!r})
from data_loader import LottoDataLoader
from number_trend_ui import render_number_trends
loader = LottoDataLoader({str(ROOT / 'Data/645_251227.csv')!r})
loader.load_data()
loader.preprocess()
loader.extract_numbers()
render_number_trends(loader)
'''


def test_trend_entry_data_range_and_view_selection():
    app = AppTest.from_string(SCRIPT, default_timeout=30).run()
    assert not app.exception and not app.error
    assert any('1249' in caption.value for caption in app.caption)
    for view in ['당첨금 배분','보너스 번호','출현 흐름']:
        app.radio(key='number_trend_view').set_value(view).run()
        assert not app.exception
    assert any('동행복권' in item.value for item in app.markdown)
