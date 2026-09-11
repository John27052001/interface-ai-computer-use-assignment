# Design Report

## 1. Architecture

I designed the system around two separate execution paths: **LLM-driven discovery** and **deterministic replay**.

During discovery, the system accepts a natural-language goal and opens the target application using Playwright. The current UI state is observed and sent to Gemini. The model chooses one structured action at a time, such as filling a field, clicking a control, or reading a value. Playwright performs the action, the application is observed again, and the observe → decide → act loop continues until the goal is complete.

A successful discovery run is converted into a versioned JSON capability artifact. The artifact is intentionally separate from the raw LLM conversation. It represents the reusable workflow rather than the model's reasoning process.

Replay follows a different path. It loads and validates the saved capability, substitutes invocation-specific inputs, resolves the recorded targets, executes the steps through Playwright, extracts declared outputs, and verifies the final checkpoint. The LLM is never called during replay.

The current implementation uses Playwright because the concrete demo surface is a web application. However, the capability represents actions and locator strategies rather than executable Playwright code. This creates a boundary between the recorded workflow and the technology used to operate a particular surface.

The project is intentionally a small single-process implementation. I did not add queues, distributed workers, databases, or deployment infrastructure because they would not improve the core computer-use design demonstrated by this vertical slice.

## 2. Artifact schema

A successful discovery produces a JSON capability such as `lookup_member_balance`.

The artifact contains a version, input contract, output contract, ordered actions, target locator strategies, and a success checkpoint. Pydantic validates the artifact before replay begins so malformed or incomplete capabilities are rejected before UI execution.

Inputs are parameterized. For example, discovery may use member `12345`, but the artifact records `{{member_id}}` rather than permanently storing that discovery value. The same capability can therefore replay with another member ID without another LLM discovery run.

Targets contain ordered locator strategies instead of a single CSS selector. For example, the Member ID input can be located by its label with an accessibility-role strategy as an alternative. The Search control uses its button role/name with a text-based fallback.

I preferred semantic and accessibility-oriented locators over DOM position or generated CSS paths because they better represent how a human identifies a control and are less tightly coupled to page structure. The replay engine tries the available strategies in order.

The artifact also declares its output (`savings_balance`) and a checkpoint requiring `Member Details` to be present. This prevents replay from treating execution of the final action as proof that the goal was actually reached.

The schema is versioned so future changes to locator representation, checkpoints, or action semantics can be handled explicitly rather than silently changing replay behavior.

## 3. Determinism & error handling

Replay is deterministic because the LLM is completely removed from the decision loop. Given a validated artifact and input parameters, the replay engine executes the recorded actions in order.

Replay distinguishes between three important classes of runtime result.

A **business outcome** is a legitimate application result that the caller needs to know about. In the demo, member `99999` produces `MEMBER_NOT_FOUND`. This is returned as `business_outcome` rather than being treated as an automation crash.

A **recoverable condition** is a known runtime state for which replay has an explicit recovery. Member `77777` displays a Security Notice. Replay recognizes the notice, dismisses it, records the recovery, and continues the saved capability.

A **hard failure** occurs when the recorded operation cannot safely continue, for example when no locator strategy can find an expected control or a checkpoint fails. The result contains the failed step, action, target, error information, and screenshot evidence when available.

The ordering of these checks is deliberate. Before extracting an output, replay first inspects the current application state for business outcomes, recoverable conditions, and intervention requirements. Only after those states are handled does it attempt to locate and extract the requested output.

At the end of a successful flow, replay verifies the artifact's checkpoint. A checkpoint mismatch becomes a structured failure rather than a false success.

Structured JSONL logs provide evidence of replay actions and outcomes, while screenshots provide additional context for selected failures.

## 4. Heterogeneity & multi-tenant

The implementation targets one web application, but I tried to keep the recorded capability separate from the concrete automation technology.

Today, Playwright resolves locator strategies and performs actions. For a legacy web application, another web surface implementation could add strategies for frames, tables, accessibility information, or other application-specific controls. For a native desktop application, the same higher-level actions could be interpreted by a surface adapter backed by OS accessibility APIs or another desktop automation mechanism.

The important boundary is:

`capability action → target description → surface-specific resolver/executor`

This allows the capability to describe *what* control is needed without requiring the artifact itself to contain Playwright code.

For multi-tenant use, I would separate the logical vendor capability from tenant-specific configuration. Institutions running the same underlying vendor application could share a base capability while supplying tenant or version-specific locator overrides only where necessary.

I would identify capabilities using the logical application/vendor and capability version rather than creating an unrelated recording for every institution. Replay success rates and checkpoint failures could then be tracked by tenant and application version. Repeated failures for one variant could trigger review or a specialized override without invalidating the shared base capability.

For production, I would also fingerprint relevant application/version characteristics and gate unattended replay when an unknown variant or meaningful drift is detected.

I did not implement multi-tenant storage or desktop automation in this project because the assignment only requires a credible design seam for those environments, and implementing infrastructure for them would add breadth without improving the core vertical slice.

## 5. Escalation & handoff

The system supports a minimal but real human-in-the-loop handoff.

Member `88888` produces a `Manager Approval Required` state. Replay does not approve the action automatically. Instead, automation pauses and transfers session ownership from `automation` to `human`.

The `SessionControl` object explicitly tracks both owner and state:

- automation / running
- human / paused
- automation / running after resume

The Playwright browser remains open throughout the handoff. The human operates the same live browser session, clicks Approve, returns to the terminal, and signals that the intervention is complete. Replay verifies that the blocking state is gone before returning ownership to automation and continuing the capability.

The handoff and resume events are recorded in the evidence log, including the session owner and state.

This implementation deliberately uses a terminal-based operator seam instead of building a full co-browsing dashboard. In a production system, the same state transition could be connected to an operator queue and remote session viewer. The important behavior demonstrated here is the ability to pause automation, preserve the live session, transfer control, verify intervention, and resume safely.

## 6. Safety

Safety checks run before replay actions are executed.

The policy layer defines an allowlist of supported action types and permitted domains. The demo is restricted to the local application (`127.0.0.1` / `localhost`). Navigation outside the configured domain is rejected.

Risky targets such as Delete Account, Close Account, and Transfer Money are blocked by policy rather than being executed automatically. In a production system, these classifications would be capability- and institution-specific rather than a small static set.

Human approval states are handled separately from known recoverable conditions. A Security Notice may be automatically dismissed because the recovery is explicitly known and reversible, while Manager Approval is escalated rather than automatically accepted.

The evidence layer also avoids persisting raw sensitive input. Member identifiers are passed to the live UI when required but are recorded as `[REDACTED]` in replay logs. API keys are supplied through environment variables and are excluded from the repository.

The current redaction implementation is intentionally small. A production implementation would use field classifications and structured redaction policies for PII, credentials, tokens, account numbers, and other regulated data rather than relying on a single generic helper.

## 7. Cuts

I deliberately kept the implementation focused on one complete vertical slice rather than adding production-scale infrastructure.

I did not build a distributed worker system, persistent database, queue, Kubernetes deployment, full operator dashboard, native desktop adapter, or production multi-tenant configuration service. Those components are useful at scale but are not necessary to demonstrate the core computer-use architecture.

The operator experience is intentionally minimal. A human takes control of the same live Playwright browser and signals completion through the terminal. With more time, I would replace this with an authenticated operator console and explicit intervention queue while preserving the same ownership/state model.

The current discovery observation uses the visible page state and selected control state rather than a full accessibility-tree or screenshot-based perception system. A next step would be to introduce a `SurfaceAdapter` interface and richer observations so the same discovery/replay contracts could support legacy web and desktop surfaces.

I would also add capability lifecycle states such as draft, reviewed, and approved; collect replay stability metrics across repeated executions; add per-vendor and per-tenant locator overrides; and require re-approval when stability or application fingerprints cross configured thresholds.

The goal of this submission is therefore not to simulate a production platform. It is to demonstrate the complete core path: a real LLM-driven discovery run, a reusable structured capability, deterministic replay with typed inputs and outputs, explicit runtime outcome handling, policy enforcement, human control transfer, and evidence for debugging and review.