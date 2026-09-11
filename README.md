# Computer-Use Automation System

Take-home engineering project for interface.ai.

This project demonstrates a computer-use automation system where an LLM learns how to complete a task through a real user interface, saves the successful workflow as a reusable capability, and later replays that capability deterministically without using the LLM again.

## Demo

The demo uses a fictional banking application called **Harbor Credit Union Operations Console**.

The main task is:

> Find a member by ID and return their savings balance.

The system works in two stages:

1. **Discovery** — Gemini observes the UI, decides what action to take, and Playwright performs the action.
2. **Replay** — the discovered capability is executed deterministically using Playwright without an LLM.

## Setup

### 1. Install dependencies

From the project folder:

```bash
pip3 install -r requirements.txt
```

Install the Playwright browser:

```bash
playwright install chromium
```

### 2. Set the Gemini API key

The Gemini API key is required only for the discovery run.

```bash
export GEMINI_API_KEY="your-api-key"
```

Never place the real API key in the source code or commit it to GitHub.

## Run the Demo Application

Start the local banking application:

```bash
python3 demo_app/app.py
```

The application runs at:

```text
http://127.0.0.1:5000
```

Keep this terminal running while using discovery or replay.

## Run LLM Discovery

Open another terminal and run:

```bash
python3 discovery.py
```

During discovery:

1. Gemini observes the current UI.
2. Gemini chooses the next action.
3. Playwright performs the action.
4. The process repeats until the goal is complete.
5. The successful workflow is saved as a reusable capability.

The generated capability is stored at:

```text
capabilities/discovered_lookup_member_balance.json
```

## Run Deterministic Replay

Replay does not use an LLM.

Run:

```bash
python3 replay.py 12345
```

Example result:

```json
{
  "status": "success",
  "outputs": {
    "savings_balance": "Savings Balance: $4820.50"
  }
}
```

The replay engine also verifies the configured success checkpoint.

## Demo Scenarios

The demo application includes several scenarios for testing runtime behavior:

| Member ID | Behavior |
| --- | --- |
| `12345` | Normal successful replay |
| `54321` | Successful replay with a different input |
| `77777` | Recoverable Security Notice |
| `88888` | Human approval and live-session handoff |
| `99999` | Member not found business outcome |

### Recoverable Condition

Run:

```bash
python3 replay.py 77777
```

A Security Notice appears. Replay detects the known condition, dismisses it, and continues automatically.

### Human Handoff

Run:

```bash
python3 replay.py 88888
```

A Manager Approval Required state appears.

Automation pauses and transfers control of the same browser session to the human operator.

Click **Approve** in the open browser, return to the terminal, and press Enter. Control returns to automation and replay continues.

### Business Outcome

Run:

```bash
python3 replay.py 99999
```

The system returns:

```json
{
  "status": "business_outcome",
  "code": "MEMBER_NOT_FOUND"
}
```

A missing member is treated as a legitimate business outcome rather than a system crash.

## Safety

The replay engine includes:

- allowed action types
- blocked risky actions
- allowed-domain validation
- human escalation for approval-required states
- sensitive input redaction in logs

The demo automation is restricted to the local application.

Sensitive member input is stored in logs as:

```text
[REDACTED]
```

## Capability Artifact

A successful discovery run produces a versioned JSON capability containing:

- input parameters
- output definitions
- ordered actions
- locator strategies
- success checkpoint

The artifact is validated with Pydantic before replay begins.

Replay refuses to execute an invalid artifact.

## Locator Strategy

Each target can contain multiple locator strategies.

For example, the Search button can first be located using its accessibility role and name, with a text-based strategy available as a fallback.

This avoids depending on a single brittle CSS selector.

## Evidence

Structured run evidence is stored in:

```text
evidence/
```

The project records evidence for:

- LLM discovery
- successful replay
- recoverable conditions
- business outcomes
- human handoff

Failure screenshots are stored in:

```text
evidence/screenshots/
```

No real customer data or credentials are used in the demo.

## Tests

Run all automated tests with:

```bash
python3 -m pytest tests/ -v
```

Tests cover:

- safety policies
- allowed domains
- sensitive-data redaction
- capability artifact structure
- session ownership and human control transfer

## Design Write-Up

Detailed architecture decisions, trade-offs, error handling, safety, human escalation, heterogeneous surfaces, multi-tenant reuse, and deliberate scope cuts are documented in:

```text
REPORT.md
```