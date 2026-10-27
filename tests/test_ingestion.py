import pandas as pd
import pytest
from download_data import COLUMNS, prepare_data, download_data


def test_missing_location_is_preserved():
    frame = pd.DataFrame([{column: None for column in COLUMNS}])
    assert len(prepare_data(frame)) == 1


def test_schema_change_fails_explicitly():
    with pytest.raises(ValueError, match="Missing source columns"):
        prepare_data(pd.DataFrame({"Make": ["TESLA"]}))


def test_http_failure_is_not_treated_as_data(monkeypatch):
    class Response:
        def raise_for_status(self):
            raise RuntimeError("upstream unavailable")
    monkeypatch.setattr("download_data.requests.get", lambda *args, **kwargs: Response())
    with pytest.raises(RuntimeError, match="upstream unavailable"):
        download_data()
