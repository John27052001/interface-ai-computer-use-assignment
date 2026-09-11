import json
import sys
from pathlib import Path

from pydantic import ValidationError
from playwright.sync_api import (
    sync_playwright,
    Error as PlaywrightError
)

from capabilities.schema import Capability
from escalation.session import SessionControl
from observability.logger import log_event
from safety.policy import check_action, check_url
from safety.redaction import redact_value


# --------------------------------------------------
# INPUT
# --------------------------------------------------

if len(sys.argv) < 2:
    print("Usage: python3 replay.py <member_id>")
    sys.exit(1)

member_id = sys.argv[1]


# --------------------------------------------------
# CHOOSE EVIDENCE LOG
# --------------------------------------------------

if member_id == "77777":
    log_file = "replay_recovery.jsonl"

elif member_id == "88888":
    log_file = "replay_handoff.jsonl"

elif member_id == "99999":
    log_file = "replay_business_outcome.jsonl"

else:
    log_file = "replay_success.jsonl"


# --------------------------------------------------
# SCREENSHOT FOLDER
# --------------------------------------------------

screenshots_dir = Path("evidence/screenshots")

screenshots_dir.mkdir(
    parents=True,
    exist_ok=True
)


# --------------------------------------------------
# LOAD + VALIDATE CAPABILITY
# --------------------------------------------------

try:

    with open(
        "capabilities/discovered_lookup_member_balance.json",
        "r"
    ) as file:
        artifact_data = json.load(file)

    validated_capability = Capability(
        **artifact_data
    )

    capability = validated_capability.model_dump()

except ValidationError as error:

    result = {
        "status": "failure",
        "error": {
            "type": "invalid_capability_artifact",
            "message": str(error)
        }
    }

    print(
        json.dumps(
            result,
            indent=2
        )
    )

    sys.exit(1)


# --------------------------------------------------
# LOCATOR HELPER
# --------------------------------------------------

def find_locator(page, target):

    strategies = target["strategies"]

    last_error = None

    for strategy in strategies:

        strategy_type = strategy["type"]

        try:

            # -------------------------
            # LABEL
            # -------------------------

            if strategy_type == "label":

                locator = page.get_by_label(
                    strategy["value"]
                )

            # -------------------------
            # ROLE
            # -------------------------

            elif strategy_type == "role":

                locator = page.get_by_role(
                    strategy["role"],
                    name=strategy["name"]
                )

            # -------------------------
            # TEXT
            # -------------------------

            elif strategy_type == "text":

                locator = page.get_by_text(
                    strategy["value"]
                )

            # -------------------------
            # CSS
            # -------------------------

            elif strategy_type == "css":

                locator = page.locator(
                    strategy["value"]
                )

            else:
                continue

            if locator.count() > 0:
                return locator

        except PlaywrightError as error:

            last_error = error

    if last_error:
        raise last_error

    raise PlaywrightError(
        "No locator strategy matched the target."
    )


# --------------------------------------------------
# FRIENDLY TARGET NAME
# --------------------------------------------------

def get_target_name(target):

    if isinstance(target, str):
        return target

    for strategy in target.get(
        "strategies",
        []
    ):

        if "name" in strategy:
            return strategy["name"]

        if "value" in strategy:
            return strategy["value"]

    return "unknown"


# --------------------------------------------------
# START REPLAY
# --------------------------------------------------

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=False
    )

    page = browser.new_page()


    # --------------------------------------------------
    # DOMAIN SAFETY CHECK
    # --------------------------------------------------

    target_url = "http://127.0.0.1:5000"

    url_policy = check_url(
        target_url
    )

    if not url_policy["allowed"]:

        result = {
            "status": "failure",
            "error": {
                "type": "policy_blocked",
                "reason": url_policy["reason"]
            }
        }

        print(
            json.dumps(
                result,
                indent=2
            )
        )

        browser.close()
        sys.exit(1)


    page.goto(
        target_url
    )


    # --------------------------------------------------
    # REPLAY STATE
    # --------------------------------------------------

    final_status = None
    outputs = {}

    session_control = SessionControl()


    # --------------------------------------------------
    # START LOG
    # --------------------------------------------------

    log_event(
        log_file,
        {
            "run_type": "replay",
            "event": "replay_started",
            "capability": capability["name"],
            "member_id": redact_value(member_id),
            "session_owner": session_control.owner,
            "session_state": session_control.state
        }
    )


    # --------------------------------------------------
    # EXECUTE SAVED STEPS
    # --------------------------------------------------

    for step_number, step in enumerate(
        capability["steps"],
        start=1
    ):

        action = step["action"]
        target = step.get("target")

        target_name = get_target_name(
            target
        )


        # --------------------------------------------------
        # ACTION SAFETY POLICY
        # --------------------------------------------------

        policy_result = check_action(
            action,
            target_name
        )

        if not policy_result["allowed"]:

            result = {
                "status": "failure",
                "error": {
                    "type": "policy_blocked",
                    "step_number": step_number,
                    "action": action,
                    "target": target_name,
                    "reason": policy_result["reason"]
                }
            }

            log_event(
                log_file,
                {
                    "run_type": "replay",
                    "event": "policy_blocked",
                    "step": step_number,
                    "action": action,
                    "target": target_name,
                    "reason": policy_result["reason"]
                }
            )

            print(
                json.dumps(
                    result,
                    indent=2
                )
            )

            final_status = "failure"
            break


        try:

            # ==================================================
            # FILL
            # ==================================================

            if action == "fill":

                locator = find_locator(
                    page,
                    target
                )

                value = step["value"].replace(
                    "{{member_id}}",
                    member_id
                )

                locator.fill(
                    value
                )

                log_event(
                    log_file,
                    {
                        "run_type": "replay",
                        "event": "step_completed",
                        "step": step_number,
                        "action": "fill",
                        "target": target_name,
                        "status": "success"
                    }
                )


            # ==================================================
            # CLICK
            # ==================================================

            elif action == "click":

                locator = find_locator(
                    page,
                    target
                )

                locator.click()

                log_event(
                    log_file,
                    {
                        "run_type": "replay",
                        "event": "step_completed",
                        "step": step_number,
                        "action": "click",
                        "target": target_name,
                        "status": "success"
                    }
                )


            # ==================================================
            # EXTRACT
            # ==================================================

            elif action == "extract":

                # First inspect page state before locating output
                page_text = page.locator(
                    "body"
                ).inner_text()


                # ==================================================
                # HUMAN HANDOFF
                # ==================================================

                if (
                    "Manager Approval Required"
                    in page_text
                ):

                    session_control.hand_to_human()

                    control_status = (
                        session_control.get_status()
                    )

                    log_event(
                        log_file,
                        {
                            "run_type": "replay",
                            "event":
                                "human_intervention_requested",
                            "step": step_number,
                            "reason":
                                "MANAGER_APPROVAL_REQUIRED",
                            "session_owner":
                                control_status["owner"],
                            "session_state":
                                control_status["state"]
                        }
                    )

                    print()
                    print(
                        "==================================="
                    )
                    print(
                        "HUMAN INTERVENTION REQUIRED"
                    )
                    print(
                        "==================================="
                    )
                    print(
                        "Reason: MANAGER_APPROVAL_REQUIRED"
                    )
                    print(
                        "Session owner:",
                        control_status["owner"]
                    )
                    print(
                        "Session state:",
                        control_status["state"]
                    )
                    print()
                    print(
                        "Please go to the open browser."
                    )
                    print(
                        "Click the Approve button manually."
                    )
                    print()

                    input(
                        "Press ENTER after approval: "
                    )

                    # Same browser session
                    page_text = page.locator(
                        "body"
                    ).inner_text()

                    if (
                        "Manager Approval Required"
                        in page_text
                    ):

                        screenshot_path = (
                            screenshots_dir
                            / "human_handoff_incomplete.png"
                        )

                        page.screenshot(
                            path=str(
                                screenshot_path
                            ),
                            full_page=True
                        )

                        result = {
                            "status": "failure",
                            "error": {
                                "type":
                                    "human_intervention_incomplete",
                                "reason":
                                    "MANAGER_APPROVAL_REQUIRED",
                                "screenshot":
                                    str(screenshot_path)
                            }
                        }

                        log_event(
                            log_file,
                            {
                                "run_type": "replay",
                                "event":
                                    "human_intervention_failed",
                                "step": step_number,
                                "status": "failure",
                                "session_owner":
                                    control_status["owner"],
                                "session_state":
                                    control_status["state"],
                                "screenshot":
                                    str(screenshot_path)
                            }
                        )

                        print(
                            json.dumps(
                                result,
                                indent=2
                            )
                        )

                        final_status = "failure"
                        break


                    # Give control back to automation
                    session_control.return_to_automation()

                    control_status = (
                        session_control.get_status()
                    )

                    print(
                        "Human intervention completed."
                    )

                    print(
                        "Automation status: RESUMED"
                    )

                    print(
                        "Session owner:",
                        control_status["owner"]
                    )

                    print(
                        "Session state:",
                        control_status["state"]
                    )

                    log_event(
                        log_file,
                        {
                            "run_type": "replay",
                            "event":
                                "human_intervention_completed",
                            "step": step_number,
                            "session_owner":
                                control_status["owner"],
                            "session_state":
                                control_status["state"],
                            "status": "resumed"
                        }
                    )


                # ==================================================
                # RECOVERABLE CONDITION
                # ==================================================

                if (
                    "Security Notice"
                    in page_text
                ):

                    print(
                        "Recoverable condition detected: "
                        "SECURITY_NOTICE"
                    )

                    log_event(
                        log_file,
                        {
                            "run_type": "replay",
                            "event":
                                "recoverable_condition_detected",
                            "step": step_number,
                            "condition":
                                "SECURITY_NOTICE"
                        }
                    )

                    page.get_by_role(
                        "button",
                        name="Dismiss"
                    ).click()

                    print(
                        "Recovery action: "
                        "dismissed Security Notice"
                    )

                    log_event(
                        log_file,
                        {
                            "run_type": "replay",
                            "event":
                                "recoverable_condition_resolved",
                            "step": step_number,
                            "condition":
                                "SECURITY_NOTICE",
                            "status":
                                "success"
                        }
                    )

                    page_text = page.locator(
                        "body"
                    ).inner_text()


                # ==================================================
                # BUSINESS OUTCOME
                # ==================================================

                if (
                    "Member not found"
                    in page_text
                ):

                    result = {
                        "status":
                            "business_outcome",
                        "code":
                            "MEMBER_NOT_FOUND"
                    }

                    log_event(
                        log_file,
                        {
                            "run_type": "replay",
                            "event":
                                "business_outcome",
                            "step": step_number,
                            "code":
                                "MEMBER_NOT_FOUND",
                            "status":
                                "business_outcome"
                        }
                    )

                    print(
                        json.dumps(
                            result,
                            indent=2
                        )
                    )

                    final_status = (
                        "business_outcome"
                    )

                    break


                # ==================================================
                # OUTPUT EXTRACTION
                # ==================================================

                locator = find_locator(
                    page,
                    target
                )

                balance = (
                    locator
                    .inner_text()
                    .replace("\n", ": ")
                )

                outputs[
                    step["output"]
                ] = balance

                log_event(
                    log_file,
                    {
                        "run_type": "replay",
                        "event":
                            "output_extracted",
                        "step": step_number,
                        "target":
                            target_name,
                        "status":
                            "success"
                    }
                )

                final_status = "success"


        # --------------------------------------------------
        # HARD FAILURE
        # --------------------------------------------------

        except PlaywrightError as error:

            screenshot_path = (
                screenshots_dir
                / f"failure_step_{step_number}.png"
            )

            try:

                page.screenshot(
                    path=str(
                        screenshot_path
                    ),
                    full_page=True
                )

                screenshot_saved = str(
                    screenshot_path
                )

            except PlaywrightError:

                screenshot_saved = (
                    "Screenshot unavailable"
                )

            result = {
                "status": "failure",
                "error": {
                    "type":
                        "playwright_error",
                    "step_number":
                        step_number,
                    "action":
                        action,
                    "target":
                        target_name,
                    "message":
                        str(error),
                    "screenshot":
                        screenshot_saved
                }
            }

            log_event(
                log_file,
                {
                    "run_type": "replay",
                    "event":
                        "hard_failure",
                    "step":
                        step_number,
                    "action":
                        action,
                    "target":
                        target_name,
                    "status":
                        "failure",
                    "message":
                        str(error),
                    "screenshot":
                        screenshot_saved
                }
            )

            print(
                json.dumps(
                    result,
                    indent=2
                )
            )

            final_status = "failure"
            break


    # --------------------------------------------------
    # CHECKPOINT
    # --------------------------------------------------

    if final_status == "success":

        checkpoint = capability.get(
            "checkpoint"
        )

        if checkpoint:

            expected_text = (
                checkpoint["value"]
            )

            page_text = page.locator(
                "body"
            ).inner_text()

            if (
                expected_text
                in page_text
            ):

                log_event(
                    log_file,
                    {
                        "run_type": "replay",
                        "event":
                            "checkpoint_passed",
                        "checkpoint":
                            expected_text,
                        "status":
                            "success"
                    }
                )

                result = {
                    "status": "success",
                    "outputs": outputs
                }

                print(
                    json.dumps(
                        result,
                        indent=2
                    )
                )

                print(
                    "Checkpoint passed:",
                    expected_text
                )

            else:

                screenshot_path = (
                    screenshots_dir
                    / "checkpoint_failure.png"
                )

                page.screenshot(
                    path=str(
                        screenshot_path
                    ),
                    full_page=True
                )

                result = {
                    "status": "failure",
                    "error": {
                        "type":
                            "checkpoint_failed",
                        "expected":
                            expected_text,
                        "observed":
                            page_text,
                        "screenshot":
                            str(screenshot_path)
                    }
                }

                log_event(
                    log_file,
                    {
                        "run_type": "replay",
                        "event":
                            "checkpoint_failed",
                        "expected":
                            expected_text,
                        "status":
                            "failure",
                        "screenshot":
                            str(screenshot_path)
                    }
                )

                print(
                    json.dumps(
                        result,
                        indent=2
                    )
                )

                final_status = "failure"


    # --------------------------------------------------
    # FINISH REPLAY
    # --------------------------------------------------

    final_control_status = (
        session_control.get_status()
    )

    log_event(
        log_file,
        {
            "run_type": "replay",
            "event":
                "replay_finished",
            "final_status":
                final_status,
            "session_owner":
                final_control_status["owner"],
            "session_state":
                final_control_status["state"]
        }
    )

    browser.close()