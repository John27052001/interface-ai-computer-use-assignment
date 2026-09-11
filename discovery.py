import json
import time

from google import genai
from google.genai.errors import ServerError, ClientError
from playwright.sync_api import sync_playwright

from observability.logger import log_event


client = genai.Client()

goal = "Find member 12345 and return their savings balance."

previous_actions = []
recorded_steps = []


# --------------------------------------------------
# GEMINI CALL WITH RETRY
# --------------------------------------------------

def ask_gemini(prompt, max_attempts=3):

    for attempt in range(1, max_attempts + 1):

        try:

            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt
            )

            return response.text.strip()

        except ServerError as error:

            if attempt < max_attempts:

                wait_seconds = attempt * 5

                print(
                    f"Gemini temporarily unavailable. "
                    f"Retrying in {wait_seconds} seconds..."
                )

                time.sleep(wait_seconds)

            else:

                print(
                    "Gemini is still unavailable after retries."
                )

                log_event(
                    "discovery_run.jsonl",
                    {
                        "run_type": "discovery",
                        "event": "llm_failure",
                        "status": "failure",
                        "error_type": "LLM_UNAVAILABLE",
                        "message": str(error)
                    }
                )

                return None

        except ClientError as error:

            print(
                "Gemini request could not continue."
            )

            log_event(
                "discovery_run.jsonl",
                {
                    "run_type": "discovery",
                    "event": "llm_failure",
                    "status": "failure",
                    "error_type": "LLM_CLIENT_ERROR",
                    "message": str(error)
                }
            )

            return None


# --------------------------------------------------
# DISCOVERY RUN
# --------------------------------------------------

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=False
    )

    page = browser.new_page()

    page.goto(
        "http://127.0.0.1:5000"
    )

    for step_number in range(5):

        print(
            "\n--- Step",
            step_number + 1,
            "---"
        )

        # -----------------------------------
        # OBSERVE CURRENT PAGE
        # -----------------------------------

        page_text = page.locator(
            "body"
        ).inner_text()

        member_input = page.get_by_label(
            "Member ID"
        )

        if member_input.count() > 0:

            current_member_id = (
                member_input.input_value()
            )

        else:

            current_member_id = (
                "NOT ON THIS PAGE"
            )

        if previous_actions:

            history = "\n".join(
                previous_actions
            )

        else:

            history = "None"


        # -----------------------------------
        # BUILD PROMPT
        # -----------------------------------

        prompt = f"""
You are controlling a web application.

Goal:
{goal}

Current visible page:
{page_text}

Current Member ID field value:
{current_member_id}

Actions already completed:
{history}

Choose exactly ONE next action.

Do not repeat an action that has already been completed successfully.

Important:
If the goal asks you to return or read information,
you MUST choose READ for that information before choosing DONE.

Only choose DONE after the requested information has been read.

Reply with only one of these formats:

FILL Member ID | 12345
CLICK Search
READ Savings Balance
DONE
"""


        # -----------------------------------
        # ASK GEMINI
        # -----------------------------------

        decision = ask_gemini(
            prompt
        )

        if decision is None:

            print(
                "Discovery stopped safely."
            )

            break

        print(
            "AI decision:"
        )

        print(
            decision
        )


        # ==================================================
        # FILL
        # ==================================================

        if decision.startswith(
            "FILL"
        ):

            parts = decision.split(
                "|"
            )

            value = (
                parts[1].strip()
            )

            page.get_by_label(
                "Member ID"
            ).fill(
                value
            )

            previous_actions.append(
                f"Filled Member ID with {value}"
            )

            recorded_steps.append(
                {
                    "action": "fill",

                    "target": {
                        "strategies": [
                            {
                                "type": "label",
                                "value": "Member ID"
                            },
                            {
                                "type": "role",
                                "role": "textbox",
                                "name": "Member ID"
                            }
                        ]
                    },

                    "value": "{{member_id}}"
                }
            )

            log_event(
                "discovery_run.jsonl",
                {
                    "run_type": "discovery",
                    "step": step_number + 1,
                    "action": "fill",
                    "target": "Member ID",
                    "status": "success"
                }
            )

            print(
                "Action performed: filled Member ID"
            )


        # ==================================================
        # CLICK
        # ==================================================

        elif decision.startswith(
            "CLICK"
        ):

            page.get_by_role(
                "button",
                name="Search"
            ).click()

            previous_actions.append(
                "Clicked Search"
            )

            recorded_steps.append(
                {
                    "action": "click",

                    "target": {
                        "strategies": [
                            {
                                "type": "role",
                                "role": "button",
                                "name": "Search"
                            },
                            {
                                "type": "text",
                                "value": "Search"
                            }
                        ]
                    }
                }
            )

            log_event(
                "discovery_run.jsonl",
                {
                    "run_type": "discovery",
                    "step": step_number + 1,
                    "action": "click",
                    "target": "Search",
                    "status": "success"
                }
            )

            print(
                "Action performed: clicked Search"
            )


        # ==================================================
        # READ
        # ==================================================

        elif decision.startswith(
            "READ"
        ):

            page_text = page.locator(
                "body"
            ).inner_text()

            if (
                "Member not found"
                in page_text
            ):

                log_event(
                    "discovery_run.jsonl",
                    {
                        "run_type": "discovery",
                        "step": step_number + 1,
                        "action": "extract",
                        "target": "Savings Balance",
                        "status": "business_outcome",
                        "code": "MEMBER_NOT_FOUND"
                    }
                )

                print(
                    "Result: MEMBER_NOT_FOUND"
                )

                break

            # -----------------------------------
            # READ SAVINGS VALUE
            # -----------------------------------

            savings_container = page.locator(
                "#savings-balance-field"
            )

            savings = (
                savings_container
                .inner_text()
                .replace("\n", ": ")
            )

            previous_actions.append(
                "Read Savings Balance"
            )

            recorded_steps.append(
                {
                    "action": "extract",

                    "target": {
                        "strategies": [
                            {
                                "type": "css",
                                "value": "#savings-balance-field"
                            },
                            {
                                "type": "text",
                                "value": "Savings Balance"
                            }
                        ]
                    },

                    "output": "savings_balance"
                }
            )

            log_event(
                "discovery_run.jsonl",
                {
                    "run_type": "discovery",
                    "step": step_number + 1,
                    "action": "extract",
                    "target": "Savings Balance",
                    "status": "success"
                }
            )

            print(
                "Result:",
                savings
            )


        # ==================================================
        # DONE
        # ==================================================

        elif decision == "DONE":

            artifact = {
                "name": "lookup_member_balance",

                "version": "1.1",

                "input": {
                    "member_id": "string"
                },

                "steps": recorded_steps,

                "output": {
                    "savings_balance": "string"
                },

                "checkpoint": {
                    "type": "text_present",
                    "value": "Member Details"
                }
            }

            with open(
                "capabilities/"
                "discovered_lookup_member_balance.json",
                "w"
            ) as file:

                json.dump(
                    artifact,
                    file,
                    indent=2
                )

            log_event(
                "discovery_run.jsonl",
                {
                    "run_type": "discovery",
                    "step": step_number + 1,
                    "action": "done",
                    "status": "success",
                    "capability":
                        "lookup_member_balance"
                }
            )

            print(
                "Capability saved."
            )

            print(
                "Goal completed."
            )

            break


        # ==================================================
        # UNKNOWN RESPONSE
        # ==================================================

        else:

            log_event(
                "discovery_run.jsonl",
                {
                    "run_type": "discovery",
                    "step": step_number + 1,
                    "action": "unknown",
                    "decision": decision,
                    "status": "failure"
                }
            )

            print(
                "Unknown AI action."
            )

            break

    browser.close()