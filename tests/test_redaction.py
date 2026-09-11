from safety.redaction import redact_value


def test_member_id_is_redacted():

    result = redact_value("12345")

    assert result == "[REDACTED]"


def test_empty_value_is_redacted():

    result = redact_value("")

    assert result == "[REDACTED]"


def test_none_value_stays_none():

    result = redact_value(None)

    assert result is None