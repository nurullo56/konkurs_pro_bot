import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from scripts.deploy import get_instance_dir, is_pm2_available

def test_get_instance_dir():
    path = get_instance_dir("test_bot")
    assert path.name == "test_bot"
    assert path.parent.name == "instances"

@patch("shutil.which")
def test_is_pm2_available(mock_which):
    mock_which.return_value = "/usr/bin/pm2"
    assert is_pm2_available() is True
    mock_which.return_value = None
    assert is_pm2_available() is False


def test_get_all_instance_names():
    from scripts.deploy import get_all_instance_names
    names = get_all_instance_names()
    assert isinstance(names, list)
    assert all(not name.startswith("__") for name in names)


@patch("scripts.deploy.restart_instance")
@patch("scripts.deploy.get_all_instance_names")
def test_restart_all_instances(mock_names, mock_restart):
    from scripts.deploy import restart_all_instances
    mock_names.return_value = ["bot_1", "bot_2"]
    restart_all_instances()
    assert mock_restart.call_count == 2
    mock_restart.assert_any_call("bot_1")
    mock_restart.assert_any_call("bot_2")


