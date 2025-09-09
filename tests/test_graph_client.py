import pytest
from unittest.mock import patch
from app.services.graph_client import GraphClient

@patch("app.services.graph_client.get_access_token", return_value="token")
@patch("requests.get")
def test_get_manager_ok(mock_get, _token):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"mail":"manager@example.com"}
    c = GraphClient()
    assert c.get_manager("user@example.com") == "manager@example.com"

@patch("app.services.graph_client.get_access_token", return_value="token")
@patch("requests.post")
def test_send_mail_accepted(mock_post, _token):
    mock_post.return_value.status_code = 202
    c = GraphClient()
    msg_id = c.send_mail("me", ["to@example.com"], [], "subj","<b>hi</b>")
    assert isinstance(msg_id, str)
