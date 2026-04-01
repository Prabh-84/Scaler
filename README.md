---
title: CascadeDebugEnv
emoji: 🐙
colorFrom: yellow
colorTo: red
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Cascading failure diagnosis environment for SRE agents
---

# CascadeDebugEnv

An **OpenEnv-compatible** reinforcement-learning environment where an agent acts as a Site Reliability Engineer (SRE) diagnosing cascading failures in a simulated microservice system.

---

## Overview

The agent receives a partial view of a distributed system (some nodes are hidden), must observe, investigate, and fix the root cause before exhausting a step budget. Every scenario has traps — actions that look correct but actively worsen the system.

### Environment Spec

| Field | Value |
|---|---|
| Action space | `observe`, `restart`, `isolate`, `rollback`, `drain_connections`, `reroute_traffic`, `scale_replica`, `declare_root_cause` |
| Observation | Partial node health, visible symptoms, active alerts, cascade risk |
| Episode termination | `declare_root_cause` action OR step budget exhausted |
| Reward | Shaped intermediate signal every step + final score from `/grader` |
| Server port | `7860` |

---

## Scenarios

Nine scenarios across three difficulty tiers:

| ID | Difficulty | Root Cause | Step Budget |
|---|---|---|---|
| easy_e1 | Easy | `auth_service` process crash | 5 |
| easy_e2 | Easy | `redis_cache` memory leak | 6 |
| easy_e3 | Easy | `postgres_primary` connection pool exhaustion | 7 |
| medium_m1 | Medium | `product_service` bad deployment (red herring trap) | 10 |
| medium_m2 | Medium | `redis_cache` full / eviction disabled | 10 |
| medium_m3 | Medium | `auth_service` TLS certificate expired | 11 |
| hard_h1 | Hard | Dual failure: `redis_cache` crash + `postgres_replica` lag | 12 |
| hard_h2 | Hard | `postgres_primary` missing index → self-amplifying retry storm | 10 |
| hard_h3 | Hard | `user_db` connection leak (decoy: `payment_gateway` looks critical) | 14 |

---

## API Endpoints

### `GET /`
Health check. Returns loaded scenario IDs.

### `GET /tasks`
Returns all available scenario IDs and the Action JSON schema.

### `GET /schema`
Returns both `Action` and `Observation` JSON schemas for client type generation.

### `POST /reset?scenario_id={id}`
Initialises a new episode. Returns the first `Observation`.

**Example:**
```bash
curl -X POST "http://localhost:7860/reset?scenario_id=easy_e1"
```

### `POST /step`
Executes one action. Returns `observation`, `reward`, `done`, `info`.

**Request body:**
```json
{
  "action": "observe",
  "target": "auth_service",
  "failure_type": null
}
```

**Response:**
```json
{
  "observation": { "step": 1, "steps_remaining": 4, "system_health": 0.74, "nodes": {...}, "active_alerts": [...], "intervention_log": [...], "cascade_risk": "medium" },
  "reward": 0.05,
  "done": false,
  "info": { "message": "" }
}
```

### `GET /state`
Returns the current observation without consuming a step.

### `GET /grader`
Returns the final score breakdown. Only callable after `done=true`.

**Response:**
```json
{
  "scenario_id": "easy_e1",
  "root_cause_accuracy": 1.0,
  "intervention_order": 0.85,
  "cascade_damage": 0.92,
  "step_efficiency": 0.75,
  "total": 0.891,
  "breakdown": { "correct_root_cause": {"node": "auth_service", "failure_type": "process_crash"}, "ground_truth_root_cause": "auth_service" }
}
```

### `GET /baseline`
Triggers the LLM agent (`inference.py`) against one easy, medium, and hard scenario and returns scores.

---

## Scoring

The final score is a weighted sum of four sub-scores:

| Criterion | Weight | Description |
|---|---|---|
| Root Cause Accuracy | 35% | Did the agent correctly identify the failing node and failure type? |
| Intervention Order | 30% | Did the agent observe before acting? Did it avoid traps? |
| Cascade Damage | 25% | How well did the agent limit damage to system health? |
| Step Efficiency | 10% | Did the agent solve it in fewer steps than optimal? |

### Intermediate Reward Shaping

Every step returns a non-zero reward signal (not just at episode end):
- `+0.05` for successfully observing a previously hidden node
- `+0.30` for applying a fix action directly to the true root-cause node
- `+0.05` for non-trap fix actions
- `-0.10` for falling into a documented trap action
- `+health × 0.10` continuous system-health incentive

---

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set your Groq API key
export OPENAI_API_KEY=gsk_...

# Start the server
uvicorn app:app --host 0.0.0.0 --port 7860

# In another terminal, run the baseline agent
python inference.py
```

---

## Docker

```bash
docker build -t cascade-debug-env .
docker run -p 7860:7860 -e OPENAI_API_KEY=gsk_... cascade-debug-env
```

---

## Project Structure

```
cascade_debug_env/
├── app.py                        # FastAPI server (main entry point)
├── inference.py                  # LLM baseline agent (Groq / llama-3.3-70b)
├── models.py                     # Pydantic models: Action, Observation, StepResponse
├── client.py                     # Legacy HTTP client (kept for reference)
├── requirements.txt
├── Dockerfile
├── openenv.yaml
├── scenarios/
│   ├── easy_e1.json … easy_e3.json
│   ├── medium_m1.json … medium_m3.json
│   └── hard_h1.json … hard_h3.json
└── server/
    ├── app.py                    # (unused, main app.py is at root)
    ├── cascade_debug_env_environment.py   # Episode state machine
    ├── cascade_engine.py         # Failure propagation + fix recovery
    └── grader.py                 # Scoring logic
```

---

## Motivation

Built for the Meta OpenEnv hackathon. The environment is designed to test whether an LLM agent can reason about dependency graphs, avoid decoy failures, and prioritise observability before irreversible interventions — skills that mirror real SRE incident response.