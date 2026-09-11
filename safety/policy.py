from urllib.parse import urlparse


ALLOWED_ACTIONS = {
    "fill",
    "click",
    "extract"
}

RISKY_TARGETS = {
    "Delete Account",
    "Close Account",
    "Transfer Money"
}

ALLOWED_DOMAINS = {
    "127.0.0.1",
    "localhost"
}


def check_action(action, target):

    if action not in ALLOWED_ACTIONS:
        return {
            "allowed": False,
            "reason": "ACTION_NOT_ALLOWED"
        }

    if target in RISKY_TARGETS:
        return {
            "allowed": False,
            "reason": "RISKY_ACTION_REQUIRES_HUMAN"
        }

    return {
        "allowed": True,
        "reason": "SAFE"
    }


def check_url(url):

    parsed = urlparse(url)

    hostname = parsed.hostname

    if hostname not in ALLOWED_DOMAINS:
        return {
            "allowed": False,
            "reason": "DOMAIN_NOT_ALLOWED"
        }

    return {
        "allowed": True,
        "reason": "SAFE"
    }