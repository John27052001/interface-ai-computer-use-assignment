from safety.policy import check_action, check_url


def test_safe_action_is_allowed():
    result = check_action("click", "Search")

    assert result["allowed"] is True
    assert result["reason"] == "SAFE"


def test_risky_action_is_blocked():
    result = check_action(
        "click",
        "Delete Account"
    )

    assert result["allowed"] is False
    assert result["reason"] == "RISKY_ACTION_REQUIRES_HUMAN"


def test_unknown_action_is_blocked():
    result = check_action(
        "download",
        "Statement"
    )

    assert result["allowed"] is False
    assert result["reason"] == "ACTION_NOT_ALLOWED"


def test_localhost_is_allowed():
    result = check_url(
        "http://127.0.0.1:5000"
    )

    assert result["allowed"] is True
    assert result["reason"] == "SAFE"


def test_external_domain_is_blocked():
    result = check_url(
        "https://example.com"
    )

    assert result["allowed"] is False
    assert result["reason"] == "DOMAIN_NOT_ALLOWED"