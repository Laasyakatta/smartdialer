# SmartDialer Dataset Analysis & Quality Report

## 1. Executive Summary

This report documents the analysis of the synthetic Collections Analytics assignment dataset, containing 17 relational CSV files, a data dictionary, and a dataset manifest. The source CSVs include borrower phone and email columns. They are intentionally excluded from this repository along with any imported database; the aggregate metrics below do not contain individual borrower records.

The synthetic dataset intentionally incorporates enterprise-style data quality cases designed to test ingestion resilience, including:
- **Exact duplicate rows** in transactional and entity logs
- **Missing / null critical identifiers** (e.g., 455 accounts lacking `borrower_id`, 1,827 calls lacking `agent_id`)
- **Mixed timezones** (UTC, `Asia/Kolkata` UTC+05:30, `Asia/Dubai` UTC+04:00) stored as naive local timestamps
- **Slowly Changing Dimensions (SCD) / Multiple Identifiers**: 30,000 agent rows representing 1,000 distinct agent entities across longitudinal updates; 30,600 borrower rows representing 11,015 distinct borrower entities
- **Legacy disposition schemas**: `PTP` vs `PROMISE_TO_PAY` across schema versions `legacy`, `v1`, and `v2`
- **Duplicate payment references** and duplicate communication events

---

## 2. Table-by-Table Metrics & Characteristics

| Dataset File | Total Rows | Primary Key | Unique PKs | Exact Duplicate Rows | Missing Values / Nulls | Timezones Present |
|---|---|---|---|---|---|---|
| `accounts.csv` | 30,000 | `account_id` | 30,000 | 0 | `borrower_id`: 455 (1.52%) | UTC (10,096), `Asia/Kolkata` (9,981), `Asia/Dubai` (9,923) |
| `account_status_history.csv` | 60,000 | `history_id` | 60,000 | 0 | None | N/A |
| `agents.csv` | 30,000 | `agent_id` | 1,000 | 0 | None | N/A |
| `agent_sessions.csv` | 15,000 | `session_id` | 15,000 | 0 | None | UTC (7,494), `Asia/Kolkata` (7,506) |
| `borrowers.csv` | 30,600 | `borrower_id` | 11,015 | 600 | `phone`: 614, `email`: 895 | N/A |
| `calls.csv` | 91,350 | `call_id` | 90,000 | 1,271 | `agent_id`: 1,827 (2.0%) | UTC (30,401), `Asia/Kolkata` (30,485), `Asia/Dubai` (30,464) |
| `call_attempts.csv` | 120,000 | `attempt_id` | 120,000 | 0 | `vendor_id`: 2,400 (2.0%) | N/A |
| `call_dispositions.csv` | 35,000 | `disposition_id` | 35,000 | 0 | None | N/A |
| `campaigns.csv` | 120 | `campaign_id` | 120 | 0 | None | N/A |
| `complaints.csv` | 8,000 | `complaint_id` | 8,000 | 0 | None | N/A |
| `daily_targeting.csv` | 45,000 | `target_id` | 45,000 | 0 | None | N/A |
| `field_visits.csv` | 25,000 | `visit_id` | 25,000 | 0 | `scheduled_at`: 250 (1.0%) | N/A |
| `payments.csv` | 25,500 | `payment_id` | 25,000 | 486 | `payment_reference`: 382 | N/A |
| `promises_to_pay.csv` | 18,000 | `ptp_id` | 18,000 | 0 | None | N/A |
| `sms_events.csv` | 45,000 | `sms_event_id` | 45,000 | 0 | None | N/A |
| `vendor_telephony.csv` | 15 | `vendor_id` | 15 | 0 | None | UTC (8), `Asia/Kolkata` (7) |
| `whatsapp_events.csv` | 60,600 | `whatsapp_event_id` | 60,000 | 600 | None | N/A |

---

## 3. Deep-Dive Anomaly Analysis

### 3.1 Agents Entity Analysis (`agents.csv`)
- **Observation**: 30,000 rows, but only 1,000 distinct `agent_id` values (e.g. `AGT0000001` through `AGT0001000`). Each agent ID repeats between 14 and 48 times (average: 30 rows per agent).
- **Root Cause**: The raw file functions as an SCD Type 2 audit log or status history log. As agents shifted teams (`T1`, `T2`, `T3`, `DIGITAL`), vendors (`VND0000001` - `VND0000015`), or statuses (`ACTIVE`, `INACTIVE`, `SUSPENDED`), new snapshot rows were appended with updated timestamps.
- **Normalization Policy**:
  1. The full raw stream is ingested into `agent_audit_history` to preserve complete audit history.
  2. The canonical `agents` table extracts the latest record per `agent_id` ordered by `updated_at DESC`.
  3. Active agents are seeded with an initial state of `OFFLINE` or `AVAILABLE` based on operational simulation requirements.

### 3.2 Borrowers Entity Analysis (`borrowers.csv`)
- **Observation**: 30,600 rows with 600 exact duplicates. There are 11,015 unique `borrower_id`s. Like `agents.csv`, multiple records exist per `borrower_id` showing profile evolution over time.
- **Data Quality Issues**:
  - 614 rows have missing phone numbers (`phone` is NULL or empty string).
  - 895 rows have missing email addresses.
  - In a small percentage of rows, `created_at` timestamp is chronologically after `updated_at`.
- **Normalization Policy**:
  1. Deduplicate exact duplicate rows and log them to `ingestion_audit_log`.
  2. Extract canonical borrower record using the highest `updated_at`.
  3. Flag borrowers with missing phones as `INELIGIBLE_FOR_VOICE`.
  4. Ensure PII masking is applied in all query responses and UI views.

### 3.3 Accounts (`accounts.csv`)
- **Observation**: 30,000 accounts. Status distribution: `ACTIVE` (7,539), `CLOSED` (7,496), `PAID` (7,486), `WRITEOFF` (7,479).
- **Data Quality Issues**:
  - 455 accounts have missing `borrower_id` (orphaned accounts).
- **Normalization Policy**:
  - Store accounts with `is_orphaned=True` when `borrower_id` is missing.
  - Borrower eligibility service strictly blocks any account that is orphaned, `CLOSED`, `PAID`, or `WRITEOFF`. Only `ACTIVE` accounts with valid borrower relationships can be dialed.

### 3.4 Calls & Historical Performance (`calls.csv`)
- **Total Calls**: 91,350 total rows; 90,000 unique `call_id`s; 1,271 exact duplicate rows; 80 duplicate call_ids with conflicting timestamps.
- **Call Direction**: Outbound (84,151 rows, 92.1%), Inbound (7,199 rows, 7.9%).
- **Call Status Distribution**:
  - `NO_ANSWER`: 18,363 (20.10%)
  - `BUSY`: 18,330 (20.07%)
  - `FAILED`: 18,276 (20.01%)
  - `VOICEMAIL`: 18,235 (19.96%)
  - `ANSWERED`: 18,146 (19.86%)
- **Historical Answer Rate**:
  $$\text{Historical Answer Rate} = \frac{\text{Answered Outbound Calls}}{\text{Total Outbound Calls}} = \frac{16,725}{84,151} \approx 19.87\%$$
  Overall answer rate across all directions is $18,146 / 91,350 \approx 19.86\%$.
- **Call Duration**: Answered calls have a mean duration of 452.9 seconds. Synthetically generated calls across all statuses also display uniform duration distributions up to 899s.
- **Unassigned Agents**: 1,827 calls have NULL `agent_id`, representing abandoned calls, system drops, or unallocated outbound attempts.

### 3.5 Dispositions & Legacy Code Mapping (`call_dispositions.csv`)
- Across 35,000 dispositions and strategy versions (`legacy`, `v1`, `v2`), codes include:
  - `PTP` (Legacy shorthand)
  - `PROMISE_TO_PAY` (Standard code)
  - `PTP_BROKEN`, `PAID`, `CALLBACK`, `REFUSED`, `DISPUTE`, `WRONG_NUMBER`, `NO_CONTACT`
- **Normalization Policy**: Standardize `PTP` to `PROMISE_TO_PAY` while preserving the raw code in `raw_disposition_code`.

### 3.6 Timestamp & Timezone Normalization
- Files containing timezone columns: `accounts.csv`, `calls.csv`, `agent_sessions.csv`, `vendor_telephony.csv`.
- Timezones represented:
  - `UTC`: No offset (+00:00)
  - `Asia/Kolkata`: Indian Standard Time (+05:30)
  - `Asia/Dubai`: Gulf Standard Time (+04:00)
- **Normalization Policy**:
  All local naive timestamps are parsed in conjunction with their row-level or vendor-level timezone, converted to ISO-8601 UTC timestamp format (`YYYY-MM-DDTHH:MM:SSZ`), and stored in SQLite. The original timezone string is retained in a dedicated column for auditability.

---

## 4. Ingestion Pipeline Architecture

```
Raw CSVs (backend/data/raw/)
       │
       ▼
Validator & Cleaner (Schema, Duplicates, Nulls, Legacy Codes)
       │
       ├── Log Flagged/Rejected Rows ──► ingestion_audit_log (DB + JSON summary)
       ▼
Normalizer (Timezone -> UTC, Code Standardization, Canonical Dedup)
       │
       ▼
SQLite Database (backend/data/smartdialer.db)
```

The pipeline guarantees:
1. **Zero Data Loss**: Raw records and audit history are captured; duplicate and malformed rows are cataloged in an audit table.
2. **Deterministic Canonical Resolution**: Entities with multiple updates select the latest verified state.
3. **UTC Standardization**: Temporal metrics can be joined and sequenced uniformly across campaigns and vendors.
