# Computer-Use Automation System

**Author:** Megha John Babu  
**Take-home assignment for interface.ai**

This project demonstrates a computer-use automation system where an LLM discovers how to complete a task through a real user interface, records the successful workflow as a reusable capability, and later replays that capability deterministically without an LLM in the decision loop.

## Demo

The demo uses a fictional banking application called **Harbor Credit Union Operations Console**.

The goal is:

> Find a member by ID and return their savings balance.

The system works in two stages:

1. **Discovery** — Gemini observes the live UI, decides the next action, and Playwright performs it.
2. **Replay** — the saved capability is executed deterministically with Playwright without calling the LLM.

## How It Works

```text
Natural-language goal
        ↓
LLM-driven discovery
        ↓
Observe → Decide → Act
        ↓
Successful workflow
        ↓
Versioned capability artifact
        ↓
Deterministic replay
        ↓
Checkpoint verification
        ↓
Structured result
```

The LLM participates only during discovery. Once a capability has been recorded, replay executes the saved steps directly.

## Setup

### 1. Install dependencies

From the project root:

```bash
pip3 install -r requirements.txt
```

Install Chromium for Playwright:

```bash
playwright install chromium
```

### 2. Configure Gemini

The Gemini API key is required only for discovery.

```bash
export GEMINI_API_KEY="your-api-key"
```

Do not place the real API key in source code or commit it to the repository.

## Start the Demo Application

Run:

```bash
python3 demo_app/app.py
```

The application will be available at `http://127.0.0.1:5000`.

Keep the demo application running while using discovery or replay.

## Run LLM Discovery

Open another terminal and run:

```bash
python3 discovery.py
```

During discovery, the system:

1. observes the current UI,
2. asks Gemini for the next action,
3. performs the action through Playwright,
4. observes the updated UI,
5. repeats until the goal is complete,
6. records the successful workflow.

A successful run produces:

`capabilities/discovered_lookup_member_balance.json`

The artifact contains parameterized inputs, ordered actions, locator strategies, outputs, and a success checkpoint.

## Run Deterministic Replay

Replay does **not** call Gemini or any other LLM.

Run:

```bash
python3 replay.py 12345
```

Example output:

```json
{
  "status": "success",
  "outputs": {
    "savings_balance": "Savings Balance: $4820.50"
  }
}
```

Replay also verifies that the expected `Member Details` checkpoint was reached.

The same capability can be reused with a different input:

```bash
python3 replay.py 54321
```

## Demo Scenarios

| Member ID | Scenario |
| --- | --- |
| `12345` | Normal successful replay |
| `54321` | Successful replay with a different input |
| `77777` | Recoverable Security Notice |
| `88888` | Human approval and live-session handoff |
| `99999` | Member-not-found business outcome |

### Recoverable Condition

Run:

```bash
python3 replay.py 77777
```

The application presents a **Security Notice**.

Replay recognizes this as a known recoverable condition, dismisses the notice, and continues execution.

### Human-in-the-Loop Handoff

Run:

```bash
python3 replay.py 88888
```

The application presents **Manager Approval Required**.

Replay pauses and transfers ownership of the existing browser session from automation to the human operator.

The operator:

1. uses the already-open Playwright browser,
2. clicks **Approve**,
3. returns to the terminal,
4. presses Enter.

The same browser session is preserved. Control is then returned to automation and replay continues.

### Business Outcome

Run:

```bash
python3 replay.py 99999
```

Result:

```json
{
  "status": "business_outcome",
  "code": "MEMBER_NOT_FOUND"
}
```

A missing member is treated as an expected business outcome rather than an automation failure.

## Capability Artifact

Discovery creates a versioned JSON capability containing:

- parameterized inputs,
- declared outputs,
- ordered actions,
- locator strategies,
- a success checkpoint.

Example:

```json
{
  "name": "lookup_member_balance",
  "version": "1.1",
  "input": {
    "member_id": "string"
  },
  "output": {
    "savings_balance": "string"
  }
}
```

The complete artifact is available at:

`capabilities/discovered_lookup_member_balance.json`

Capabilities are validated with Pydantic before replay begins. Invalid artifacts are rejected before browser automation starts.

## Locator Strategy

Targets use ordered locator strategies instead of relying on one brittle selector.

The implementation supports:

- label-based locators,
- accessibility role/name locators,
- text locators,
- CSS locators.

This separates the logical capability from a single DOM selector and provides a clean seam for supporting less structured application surfaces.

## Runtime Error Handling

Replay distinguishes between:

- **Success** — the task completed and declared outputs were returned.
- **Business outcome** — the application returned a legitimate result such as `MEMBER_NOT_FOUND`.
- **Recoverable condition** — a known interruption can be handled safely and replay continues.
- **Hard failure** — replay cannot safely continue and returns structured diagnostic information.

Checkpoint failures and Playwright failures are surfaced as structured errors rather than silently proceeding.

## Safety

The replay engine includes:

- an allowlist of supported action types,
- an allowlist of permitted domains,
- blocking of risky or irreversible targets,
- human escalation for approval-required states,
- sensitive-input redaction in logs.

The demo automation is restricted to `localhost` / `127.0.0.1`.

Sensitive member input is recorded in evidence logs as:

```text
[REDACTED]
```

rather than persisting the raw identifier.

## Evidence and Observability

Structured evidence is stored under `evidence/`.

The repository includes:

- `evidence/discovery_run.jsonl`
- `evidence/replay_success.jsonl`
- `evidence/replay_recovery.jsonl`
- `evidence/replay_handoff.jsonl`
- `evidence/replay_business_outcome.jsonl`
- `evidence/example_capability.json`

Failure screenshots are stored under `evidence/screenshots/`.

The evidence demonstrates the real LLM-driven discovery run as well as deterministic replay and exceptional runtime states.

## Tests

Run the complete test suite with:

```bash
python3 -m pytest tests/ -v
```

Tests cover:

- action safety policies,
- domain restrictions,
- sensitive-data redaction,
- capability artifact structure,
- locator metadata,
- checkpoint configuration,
- human/automation session ownership.

## Project Structure

```text
.
├── capabilities/
│   ├── discovered_lookup_member_balance.json
│   └── schema.py
│
├── demo_app/
│   ├── app.py
│   └── templates/
│
├── escalation/
│   └── session.py
│
├── evidence/
│   ├── screenshots/
│   └── ...
│
├── observability/
│   └── logger.py
│
├── safety/
│   ├── policy.py
│   └── redaction.py
│
├── tests/
│
├── discovery.py
├── replay.py
├── requirements.txt
├── README.md
└── REPORT.md
```

## Design Report

Architecture decisions, artifact design, deterministic replay, error handling, heterogeneous-surface considerations, multi-tenant reuse, human handoff, safety, trade-offs, and deliberate scope cuts are documented in:

`REPORT.md`