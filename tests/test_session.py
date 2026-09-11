from escalation.session import SessionControl


def test_session_starts_with_automation():

    session = SessionControl()

    status = session.get_status()

    assert status["owner"] == "automation"
    assert status["state"] == "running"


def test_handoff_to_human():

    session = SessionControl()

    session.hand_to_human()

    status = session.get_status()

    assert status["owner"] == "human"
    assert status["state"] == "paused"


def test_return_to_automation():

    session = SessionControl()

    session.hand_to_human()
    session.return_to_automation()

    status = session.get_status()

    assert status["owner"] == "automation"
    assert status["state"] == "running"