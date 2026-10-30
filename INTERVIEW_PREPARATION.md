# SmartDialer Interview Preparation

These notes describe the implementation in this repository. The system is a
local assignment prototype with mock telecom providers; it is not a
production-ready or compliance-certified dialer.

## Architecture and design

### 1. What does SmartDialer do?

It models an outbound collections dialing workflow. A FastAPI backend exposes
operations APIs and coordinates dialing services, safety checks, persistence,
event processing, and simulations. A React dashboard consumes those APIs.

### 2. What are the main technology choices?

The backend uses Python, FastAPI, SQLAlchemy, Pydantic, and SQLite. The
frontend uses React, Vite, React Router, Axios, and Recharts. The backend test
suite uses pytest and an in-memory SQLite fixture.

### 3. What is the high-level request flow?

The dashboard calls FastAPI through the Vite development proxy. API routes
invoke services that read and update SQLAlchemy models. Dialing services
consult the Safety Controller before allocating calls; mock provider events
are passed to the event processor.

### 4. How are the backend and frontend organized?

`backend/app/api` contains route handlers; `models` and `schemas` define
persistence and API data shapes; `services` contains workflow logic; and
`providers` implements mock telecom providers. `frontend/src` contains the
React app, reusable components, pages, and API client.

### 5. Why use a separate Safety Controller?

Pacing expresses a desired call volume, not permission to place calls. A
separate controller rechecks capacity and other constraints before allocation,
so a predictive proposal cannot directly trigger a provider call.

## Dialing and safety

### 6. How does progressive dialing work?

`ProgressiveDialerService` checks agent availability and borrower eligibility,
submits a bounded request to the Safety Controller, reserves agents, and
allocates calls only up to the approved count. Unused reservations are
released.

### 7. What is predictive dialing in this project?

`PredictiveDialerService` asks `PredictivePacingEngine` for a proposal based
on available agents and historical call performance. The service passes the
proposal through the Safety Controller before reserving agents or allocating
calls.

### 8. Can the predictive engine place calls itself?

No. It generates a pacing proposal. The predictive dialer service sends that
proposal to the Safety Controller and continues only based on the controller's
decision.

### 9. What happens when the safety decision requests progressive fallback?

The predictive service invokes `ProgressiveDialerService` for that cycle,
preserving a one-agent-at-a-time allocation path.

### 10. What limits does the Safety Controller consider?

It considers provider health, campaign and system capacity, available-agent
capacity, and whether a borrower already has an active call. Exact outcomes
are represented by the safety decision type and evaluation result.

### 11. How does the code protect against assigning an agent twice?

The agent state machine uses conditional database updates and state
transitions to reserve available agents. Dedicated concurrency tests exercise
contention for reservations.

### 12. How is borrower eligibility handled?

`EligibilityService` filters candidate borrowers and accounts using
campaign-related status and risk rules before a dialing cycle proposes work.
The API response path also applies phone and email masking helpers.

### 13. How are call state transitions managed?

`CallStateMachine` owns call transitions and guards against invalid or
terminal-state overwrites. Provider callbacks are processed through
`EventProcessor`, which records events and handles duplicate or late events.

### 14. How do mock providers differ?

Both providers implement the shared provider interface. Their configured
latency/failure behavior differs, and Provider B can simulate duplicated or
out-of-order events. They generate simulated events rather than contacting
telecom networks.

### 15. What does the circuit breaker contribute?

It tracks provider failures and recovery state so unhealthy provider
conditions can inform dialing safety decisions. Provider state is currently
in-process, which is a limitation for a multi-worker deployment.

### 16. How does recovery work?

`RecoveryService` contains reconciliation routines for stale reservations and
calls. The application lifespan invokes stale-reservation reconciliation at
startup; tests cover failure-recovery behavior.

### 17. How are simulations isolated?

Simulation records carry simulation-related identifiers/flags, allowing
simulation workflows and queries to distinguish them from normal call data.
The simulation endpoint exercises the same service-level dialing concepts.

## Data and persistence

### 18. Why SQLite?

SQLite keeps the assignment easy to run locally without a separate database
service. WAL mode improves read concurrency, but SQLite still serializes
writes and is not the recommended choice for a high-write production system.

### 19. What does the ingestion pipeline do?

`backend/ingestion/run_ingestion.py` reads expected CSV inputs, applies
normalization helpers from `normalizer.py`, loads records into SQLite, and
writes a local ingestion summary. It is optional for running the tests.

### 20. Why are the dataset and generated database excluded from Git?

The local synthetic borrower dataset includes contact fields, and the
generated database contains imported records. Keeping both out of version
control reduces privacy and repository-size risks. The assignment data must
be obtained separately for local ingestion.

### 21. What timezone handling is present?

The ingestion normalizer includes timestamp parsing and normalization helpers
for source data that may have timezone context. The source timezone is
important when interpreting naive timestamps.

### 22. How would you make ingestion safer for production?

I would validate schemas before destructive database operations, make imports
transactional and repeatable, use configurable input/output locations, add
reconciliation tests, and avoid logging row-level sensitive information.

## Testing and operations

### 23. How are backend tests isolated from local data?

The shared pytest fixture creates an in-memory SQLite database, creates the
ORM schema for each test, then closes and drops it. Tests do not need the
borrower dataset or the local application database.

### 24. What behaviors are covered by tests?

The test modules cover state machines, borrower eligibility, provider events,
progressive and predictive pacing, safety decisions, concurrency, and
recovery. `test_load.py` exercises a basic workload.

### 25. How do you run the backend tests?

From the repository root, install `backend/requirements.txt` in a Python
environment and run `python -m pytest backend/tests -v`.

### 26. How do you build the frontend?

Run `npm ci` and then `npm run build` in `frontend/`. The package does not
currently define a frontend test script.

### 27. What is needed to run the app locally?

Python 3.11 or newer, Node.js/npm, backend requirements, and frontend npm
dependencies. The backend defaults to SQLite and the frontend Vite server
proxies API requests to port 8000.

### 28. What are the most important production gaps?

Authentication and authorization, restrictive CORS, durable shared provider
state, a production database, monitoring, background execution for lengthy
simulations, and legal/compliance review are all required before real-world
use.

### 29. How would you scale the persistence layer?

I would first measure the workload, then consider PostgreSQL and explicit
transaction/locking strategies for concurrent allocation. I would also
externalize shared state and add migrations, observability, and load tests
that reflect realistic concurrency.

### 30. What would you improve next in the frontend?

I would add automated component and integration tests, improve loading and
empty states, and use route-level code splitting if bundle measurements
justify it. The current production build reports a large JavaScript chunk.

### 31. How should the system be evaluated as an assignment?

Review the service boundaries, state transition rules, safety checks, test
coverage, and local setup flow. Treat the providers and data as demonstrations,
not evidence of a deployed telephony system or production compliance.
