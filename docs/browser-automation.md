# Browser Automation

## What Exists In This Repository

The public repository includes an isolated applicant-agent container intended for browser-driven automation experiments.

Relevant files:

- `Dockerfile.agent`
- `app/agents/applicant_agent.py`
- `scripts/vnc_entrypoint.sh`
- `docker-compose.yml`

## Isolation Model

The agent image is set up to:

- run as a non-root user
- install Playwright and browser dependencies separately from the main API image
- expose a VNC-accessible virtual display
- mount application code and runtime artifact directories with restricted intent

This makes the automation environment easier to inspect and safer to reason about than running everything inside the main backend container.

## VNC Access

The agent profile exposes port `5900`.

Before using it, set a non-default password in `.env`:

```bash
VNC_PASSWORD=your-strong-local-password
```

Then start the agent profile:

```bash
docker-compose --profile agent up --build agent
```

## Current State

The browser automation path is not a fully complete portal-automation product in the public repo.

What is visible today:

- orchestration scaffolding
- portal-type detection logic
- isolated runtime image
- ATS detection primitives with Playwright-driven evidence capture

What should be treated as incomplete or experimental:

- portal-specific submission coverage
- end-to-end production-safe application submission
- account/email verification loops for all target portals

## Handling Artifacts Safely

Treat all automation artifacts as sensitive by default:

- screenshots
- logs
- browser auth/session files
- captured network traces
- downloaded candidate documents

These should remain untracked locally and should never be committed.
