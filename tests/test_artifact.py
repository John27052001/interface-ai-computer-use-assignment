import json


ARTIFACT_PATH = (
    "capabilities/discovered_lookup_member_balance.json"
)


def load_artifact():
    with open(ARTIFACT_PATH, "r") as file:
        return json.load(file)


def test_artifact_has_name_and_version():
    artifact = load_artifact()

    assert artifact["name"] == "lookup_member_balance"
    assert artifact["version"] == "1.1"


def test_artifact_has_input():
    artifact = load_artifact()

    assert "input" in artifact
    assert "member_id" in artifact["input"]
    assert artifact["input"]["member_id"] == "string"


def test_artifact_has_output():
    artifact = load_artifact()

    assert "output" in artifact
    assert "savings_balance" in artifact["output"]
    assert artifact["output"]["savings_balance"] == "string"


def test_artifact_has_steps():
    artifact = load_artifact()

    assert "steps" in artifact
    assert len(artifact["steps"]) > 0


def test_every_step_has_action_and_target():
    artifact = load_artifact()

    for step in artifact["steps"]:
        assert "action" in step
        assert "target" in step


def test_every_target_has_locator_strategy():
    artifact = load_artifact()

    for step in artifact["steps"]:

        target = step["target"]

        assert "strategies" in target
        assert len(target["strategies"]) > 0


def test_artifact_has_checkpoint():
    artifact = load_artifact()

    assert "checkpoint" in artifact

    assert (
        artifact["checkpoint"]["type"]
        == "text_present"
    )

    assert (
        artifact["checkpoint"]["value"]
        == "Member Details"
    )