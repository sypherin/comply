from app.services.auth_easy_auth import get_user_from_easy_auth

def test_easy_auth_from_debug_headers():
    user = get_user_from_easy_auth({"X-DEBUG-EMAIL":"u@example.com","X-DEBUG-NAME":"U"})
    assert user["email"] == "u@example.com"
