import pytest
import sys
from unittest.mock import patch
from core.config import load_config

def test_load_config_missing_file(capsys):
    with patch("os.path.isfile", return_value=False):
        with pytest.raises(SystemExit) as exc:
            load_config()
        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "CRITICAL ERROR: Required configuration file not found" in captured.out
