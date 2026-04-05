
# Cascade Debug Environment

### Root Cause Discovery in Distributed Microservice Failures

## Overview

Cascade Debug Environment is a simulated distributed microservice system where failures propagate across services.
An AI agent interacts with the system, investigates failures, performs interventions, and must identify the **original root cause** before running out of steps.

The environment is designed so that **fixing the obvious broken service is often wrong** — the real issue is usually upstream.

This project simulates real-world **SRE debugging, incident response, and cascading system failures**.

---

## Problem Statement

In distributed systems:

* One service fails
* Other services start failing
* Alerts point to multiple services
* Restarting broken services may not fix the system
* The real issue is often a database, cache, deployment, or configuration

This environment tests whether an agent can:

1. Observe the system
2. Understand dependencies
3. Avoid traps
4. Identify the root cause
5. Minimize cascade damage

---

## Features

* Simulated microservice architecture
* Failure propagation engine
* Hidden node health and observability
* Step budget (limited actions)
* Trap actions and decoy failures
* Multiple difficulty scenarios
* Scoring system for agent performance
* FastAPI environment server
* LLM-powered debugging agent
* Frontend visualization dashboard (Topology, Logs, Node Details)

---

## System Architecture

The simulated system includes services like:

* API Gateway
* Auth Service
* Product Service
* Order Service
* User DB
* Postgres Primary & Replica
* Redis Cache
* CDN Cache
* Payment Gateway

Failures propagate through service dependencies, causing **cascade failures** across the system.

---

## Scenarios

Scenarios are stored in the `scenarios/` folder and include:

* Easy scenarios (single failure)
* Medium scenarios (traps and misleading alerts)
* Hard scenarios (multiple failures, retry storms, hidden root causes)

Each scenario defines:

* Initial system state
* Failure injections
* Step budget
* Trap actions
* Ground truth root cause

---

## Available Actions

The agent can perform the following actions:

| Action             | Purpose                            |
| ------------------ | ---------------------------------- |
| observe            | Reveal hidden health/logs          |
| restart            | Restart a service                  |
| isolate            | Isolate a service                  |
| rollback           | Rollback deployment                |
| drain_connections  | Drain DB/service connections       |
| reroute_traffic    | Redirect traffic                   |
| scale_replica      | Scale service                      |
| declare_root_cause | End episode and declare root cause |

---

## Scoring System

The agent is evaluated on:

| Metric              | Description                   |
| ------------------- | ----------------------------- |
| Root Cause Accuracy | Correct root cause identified |
| Intervention Order  | Observed before acting        |
| Cascade Damage      | System health preserved       |
| Step Efficiency     | Solved in fewer steps         |

Final score is a weighted combination of these metrics.

---

## Project Structure

```
cascade_debug_env/
│
├── chaos-frontend/        # Frontend visualization (Next.js)
│   ├── app/
│   ├── components/
│   └── lib/
│
├── scenarios/             # Failure scenarios
│
├── server/                # Environment engine
│   ├── app.py
│   ├── cascade_engine.py
│   ├── cascade_debug_env_environment.py
│   └── grader.py
│
├── client.py              # LLM agent client
├── inference.py           # Agent inference runner
├── models.py
├── Dockerfile
├── requirements.txt
├── openenv.yaml
└── README.md
```

---

## Running the Project

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Environment Server

```bash
uvicorn server.app:app --reload --port 8000
```

### 3. Run AI Agent

```bash
python client.py
```

### 4. Run Frontend

```bash
cd chaos-frontend
npm install
npm run dev
```

---

## API Endpoints

| Endpoint      | Description        |
| ------------- | ------------------ |
| GET /         | Health check       |
| GET /tasks    | List scenarios     |
| POST /reset   | Start scenario     |
| GET /state    | Get system state   |
| POST /step    | Execute action     |
| GET /grader   | Get final score    |
| GET /baseline | Run baseline agent |

---

## What This Project Demonstrates

* Distributed systems debugging
* Failure propagation modeling
* Root cause analysis
* AI agent decision making
* Incident response simulation
* Observability and SRE workflows
* Reinforcement learning environment design

---

## Summary

Cascade Debug Environment is a **distributed system failure simulation** where an AI agent must:

* Investigate failures
* Understand service dependencies
* Avoid misleading signals
* Identify the true root cause
* Minimize system damage
* Solve within limited steps

It is essentially a **debugging environment for AI agents in distributed systems**.

---