"""
Complete Enterprise Data Ingestion Pipeline
"""
import os
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import insert

from backend.app.core.database import SessionLocal, engine, Base
import backend.app.models as m
from backend.ingestion.normalizer import (
    parse_and_normalize_timestamp,
    normalize_disposition_code,
    clean_phone,
    clean_email
)

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
SUMMARY_FILE = Path(__file__).resolve().parent.parent / "data" / "cleaned" / "ingestion_summary.json"

BATCH_SIZE = 5000

def get_csv_reader(filename):
    filepath = RAW_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Dataset file {filename} not found at {filepath}")
    fp = open(filepath, "r", encoding="utf-8", errors="replace")
    reader = csv.DictReader(fp)
    return fp, reader

def run_pipeline():
    start_time = time.time()
    print("=" * 60)
    print("Starting SmartDialer Data Ingestion Pipeline...")
    print("=" * 60)

    # Recreate all tables cleanly
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tables": {},
        "audit_issues": {
            "duplicate_rows": 0,
            "missing_required_fields": 0,
            "orphaned_foreign_keys": 0,
            "legacy_codes_mapped": 0,
            "timestamp_inversions": 0,
        }
    }

    audit_logs = []

    def log_issue(table: str, row_id: str | None, issue_type: str, details: str):
        audit_logs.append({
            "table_name": table,
            "row_identifier": str(row_id) if row_id else None,
            "issue_type": issue_type,
            "details": details,
            "created_at": datetime.now(timezone.utc)
        })
        if issue_type == "DUPLICATE_ROW":
            summary["audit_issues"]["duplicate_rows"] += 1
        elif issue_type == "MISSING_FIELD":
            summary["audit_issues"]["missing_required_fields"] += 1
        elif issue_type == "ORPHANED_FK":
            summary["audit_issues"]["orphaned_foreign_keys"] += 1
        elif issue_type == "LEGACY_CODE":
            summary["audit_issues"]["legacy_codes_mapped"] += 1

    try:
        # 1. Vendor Telephony
        print("Ingesting vendor_telephony...")
        fp, r = get_csv_reader("vendor_telephony.csv")
        vendor_rows = []
        for row in r:
            vendor_rows.append({
                "vendor_id": row["vendor_id"],
                "vendor_name": row["vendor_name"],
                "vendor_account_id": row.get("vendor_account_id"),
                "timezone": row.get("timezone"),
                "status": row.get("status", "ACTIVE"),
                "schema_version": row.get("schema_version")
            })
        fp.close()
        db.bulk_insert_mappings(m.VendorTelephony, vendor_rows)
        db.commit()
        summary["tables"]["vendor_telephony"] = len(vendor_rows)

        # 2. Campaigns
        print("Ingesting campaigns...")
        fp, r = get_csv_reader("campaigns.csv")
        campaign_rows = []
        for row in r:
            campaign_rows.append({
                "campaign_id": row["campaign_id"],
                "campaign_name": row["campaign_name"],
                "channel": row.get("channel"),
                "strategy_version": row.get("strategy_version"),
                "dialing_mode": "PROGRESSIVE",
                "target_definition": row.get("target_definition"),
                "is_active": True,
                "start_at": parse_and_normalize_timestamp(row.get("start_at")),
                "end_at": parse_and_normalize_timestamp(row.get("end_at")),
                "max_concurrent_calls": 50,
                "target_answer_rate": 0.20,
                "safety_margin": 0.15,
                "is_simulation": False
            })
        fp.close()
        db.bulk_insert_mappings(m.Campaign, campaign_rows)
        db.commit()
        summary["tables"]["campaigns"] = len(campaign_rows)

        # 3. Agents
        print("Ingesting agents & agent audit history...")
        fp, r = get_csv_reader("agents.csv")
        agent_audit_rows = []
        latest_agents = {}
        for row in r:
            up_dt = parse_and_normalize_timestamp(row.get("updated_at"))
            joined_dt = parse_and_normalize_timestamp(row.get("joined_at"))
            agent_audit_rows.append({
                "agent_id": row["agent_id"],
                "employee_code": row.get("employee_code"),
                "agent_name": row.get("agent_name", "Unknown"),
                "vendor_id": row.get("vendor_id"),
                "team": row.get("team"),
                "status": row.get("status", "ACTIVE"),
                "joined_at": joined_dt,
                "updated_at": up_dt or datetime.now(timezone.utc)
            })
            aid = row["agent_id"]
            if aid not in latest_agents or (up_dt and up_dt > latest_agents[aid]["updated_at"]):
                latest_agents[aid] = {
                    "agent_id": aid,
                    "employee_code": row.get("employee_code"),
                    "agent_name": row.get("agent_name", "Unknown"),
                    "vendor_id": row.get("vendor_id"),
                    "team": row.get("team"),
                    "status": "AVAILABLE" if row.get("status") == "ACTIVE" else "OFFLINE",
                    "current_call_id": None,
                    "reserved_at": None,
                    "last_status_change": datetime.now(timezone.utc),
                    "joined_at": joined_dt,
                    "updated_at": up_dt or datetime.now(timezone.utc),
                    "is_simulation": False,
                    "simulation_id": None
                }
        fp.close()

        # Batch insert agent history
        for i in range(0, len(agent_audit_rows), BATCH_SIZE):
            db.bulk_insert_mappings(m.AgentAuditHistory, agent_audit_rows[i:i+BATCH_SIZE])
        db.commit()

        # Batch insert canonical agents
        canonical_agents_list = list(latest_agents.values())
        for i in range(0, len(canonical_agents_list), BATCH_SIZE):
            db.bulk_insert_mappings(m.Agent, canonical_agents_list[i:i+BATCH_SIZE])
        db.commit()
        summary["tables"]["agents_canonical"] = len(canonical_agents_list)
        summary["tables"]["agent_audit_history"] = len(agent_audit_rows)

        # 4. Borrowers
        print("Ingesting borrowers & deduplicating...")
        fp, r = get_csv_reader("borrowers.csv")
        borrower_audit_rows = []
        latest_borrowers = {}
        seen_exact_borrowers = set()
        for row in r:
            row_tuple = (row["borrower_id"], row.get("name"), row.get("phone"), row.get("email"), row.get("city"), row.get("state"))
            if row_tuple in seen_exact_borrowers:
                log_issue("borrowers", row["borrower_id"], "DUPLICATE_ROW", "Exact duplicate borrower row detected")
                continue
            seen_exact_borrowers.add(row_tuple)

            c_dt = parse_and_normalize_timestamp(row.get("created_at"))
            u_dt = parse_and_normalize_timestamp(row.get("updated_at"))
            if c_dt and u_dt and c_dt > u_dt:
                summary["audit_issues"]["timestamp_inversions"] += 1

            borrower_audit_rows.append({
                "borrower_id": row["borrower_id"],
                "name": row.get("name", "Unknown"),
                "phone": row.get("phone"),
                "email": row.get("email"),
                "city": row.get("city"),
                "state": row.get("state"),
                "created_at": c_dt,
                "updated_at": u_dt
            })

            bid = row["borrower_id"]
            cleaned_p = clean_phone(row.get("phone"))
            cleaned_e = clean_email(row.get("email"))

            is_eligible = True
            reason = None
            if not cleaned_p:
                is_eligible = False
                reason = "MISSING_PHONE_NUMBER"
                log_issue("borrowers", bid, "MISSING_FIELD", "Borrower missing contact phone number")

            if bid not in latest_borrowers or (u_dt and latest_borrowers[bid]["updated_at"] and u_dt > latest_borrowers[bid]["updated_at"]):
                latest_borrowers[bid] = {
                    "borrower_id": bid,
                    "name": row.get("name", "Unknown"),
                    "phone": cleaned_p,
                    "email": cleaned_e,
                    "city": row.get("city"),
                    "state": row.get("state"),
                    "is_eligible": is_eligible,
                    "ineligibility_reason": reason,
                    "current_active_call_id": None,
                    "reserved_at": None,
                    "created_at": c_dt or datetime.now(timezone.utc),
                    "updated_at": u_dt or datetime.now(timezone.utc),
                    "is_simulation": False
                }
        fp.close()

        for i in range(0, len(borrower_audit_rows), BATCH_SIZE):
            db.bulk_insert_mappings(m.BorrowerAuditHistory, borrower_audit_rows[i:i+BATCH_SIZE])
        db.commit()

        canonical_borrowers_list = list(latest_borrowers.values())
        for i in range(0, len(canonical_borrowers_list), BATCH_SIZE):
            db.bulk_insert_mappings(m.Borrower, canonical_borrowers_list[i:i+BATCH_SIZE])
        db.commit()
        summary["tables"]["borrowers_canonical"] = len(canonical_borrowers_list)
        summary["tables"]["borrower_audit_history"] = len(borrower_audit_rows)

        # 5. Accounts
        print("Ingesting accounts...")
        fp, r = get_csv_reader("accounts.csv")
        account_rows = []
        for row in r:
            tz = row.get("timezone", "UTC")
            opened_dt = parse_and_normalize_timestamp(row.get("opened_at"), tz)
            bid = row.get("borrower_id")
            is_orphaned = False
            if not bid or bid.lower() in ("null", "none", "", "nan"):
                is_orphaned = True
                bid = None
                log_issue("accounts", row["account_id"], "ORPHANED_FK", "Account has null borrower_id")

            account_rows.append({
                "account_id": row["account_id"],
                "borrower_id": bid,
                "loan_type": row.get("loan_type"),
                "principal_amount": float(row.get("principal_amount") or 0.0),
                "outstanding_amount": float(row.get("outstanding_amount") or 0.0),
                "dpd": int(row.get("dpd") or 0),
                "risk_segment": row.get("risk_segment"),
                "status": row.get("status", "ACTIVE"),
                "opened_at": opened_dt,
                "timezone": tz,
                "schema_version": row.get("schema_version"),
                "is_orphaned": is_orphaned
            })
        fp.close()
        for i in range(0, len(account_rows), BATCH_SIZE):
            db.bulk_insert_mappings(m.Account, account_rows[i:i+BATCH_SIZE])
        db.commit()
        summary["tables"]["accounts"] = len(account_rows)

        # 6. Account Status History
        print("Ingesting account_status_history...")
        fp, r = get_csv_reader("account_status_history.csv")
        history_rows = []
        for row in r:
            ev_dt = parse_and_normalize_timestamp(row.get("event_at"))
            rec_dt = parse_and_normalize_timestamp(row.get("recorded_at"))
            bid = row.get("borrower_id")
            if not bid or bid.lower() in ("null", "none", ""): bid = None
            history_rows.append({
                "history_id": row["history_id"],
                "account_id": row["account_id"],
                "borrower_id": bid,
                "event_at": ev_dt or datetime.now(timezone.utc),
                "status": row.get("status", "ACTIVE"),
                "changed_by": row.get("changed_by"),
                "source": row.get("source"),
                "recorded_at": rec_dt or datetime.now(timezone.utc)
            })
        fp.close()
        for i in range(0, len(history_rows), BATCH_SIZE):
            db.bulk_insert_mappings(m.AccountStatusHistory, history_rows[i:i+BATCH_SIZE])
        db.commit()
        summary["tables"]["account_status_history"] = len(history_rows)

        # 7. Daily Targeting
        print("Ingesting daily_targeting...")
        fp, r = get_csv_reader("daily_targeting.csv")
        target_rows = []
        for row in r:
            tgt_dt = parse_and_normalize_timestamp(row.get("target_date"))
            target_rows.append({
                "target_id": row["target_id"],
                "account_id": row["account_id"],
                "campaign_id": row["campaign_id"],
                "target_date": tgt_dt or datetime.now(timezone.utc),
                "priority": int(row.get("priority") or 1),
                "recommended_channel": row.get("recommended_channel"),
                "status": row.get("status", "QUEUED")
            })
        fp.close()
        for i in range(0, len(target_rows), BATCH_SIZE):
            db.bulk_insert_mappings(m.DailyTargeting, target_rows[i:i+BATCH_SIZE])
        db.commit()
        summary["tables"]["daily_targeting"] = len(target_rows)

        # 8. Calls
        print("Ingesting calls & normalizing timestamps...")
        fp, r = get_csv_reader("calls.csv")
        call_rows = []
        seen_calls = set()
        for row in r:
            cid = row["call_id"]
            if cid in seen_calls:
                log_issue("calls", cid, "DUPLICATE_ROW", "Duplicate call ID row ignored")
                continue
            seen_calls.add(cid)

            tz = row.get("timezone", "UTC")
            ev_dt = parse_and_normalize_timestamp(row.get("event_at"), tz)
            aid = row.get("agent_id")
            if not aid or aid.lower() in ("null", "none", "", "nan"):
                aid = None
                log_issue("calls", cid, "MISSING_FIELD", "Historical call has no allocated agent")

            dur = int(row.get("duration_sec") or 0)
            status = row.get("call_status", "COMPLETED")

            # Map raw status to CallState enum
            if status == "ANSWERED":
                call_state = m.CallState.COMPLETED.value
                terminal_reason = "ANSWERED_NORMAL"
            elif status in ("NO_ANSWER", "BUSY", "VOICEMAIL"):
                call_state = m.CallState.COMPLETED.value
                terminal_reason = status
            elif status == "FAILED":
                call_state = m.CallState.FAILED.value
                terminal_reason = "PROVIDER_FAILED"
            else:
                call_state = m.CallState.COMPLETED.value
                terminal_reason = status

            call_rows.append({
                "call_id": cid,
                "campaign_id": row.get("campaign_id"),
                "account_id": row["account_id"],
                "borrower_id": row["borrower_id"],
                "agent_id": aid,
                "vendor_id": row.get("vendor_id"),
                "provider_name": "historical",
                "direction": row.get("direction", "OUTBOUND"),
                "state": call_state,
                "terminal_reason": terminal_reason,
                "duration_sec": dur,
                "queued_at": ev_dt or datetime.now(timezone.utc),
                "reserved_at": ev_dt,
                "initiated_at": ev_dt,
                "ringing_at": ev_dt,
                "answered_at": ev_dt if status == "ANSWERED" else None,
                "connected_at": ev_dt if status == "ANSWERED" else None,
                "completed_at": ev_dt,
                "timezone": tz,
                "is_simulation": False,
                "simulation_id": None
            })
        fp.close()
        for i in range(0, len(call_rows), BATCH_SIZE):
            db.bulk_insert_mappings(m.Call, call_rows[i:i+BATCH_SIZE])
        db.commit()
        summary["tables"]["calls"] = len(call_rows)

        # 9. Call Attempts
        print("Ingesting call_attempts...")
        fp, r = get_csv_reader("call_attempts.csv")
        attempt_rows = []
        for row in r:
            ev_dt = parse_and_normalize_timestamp(row.get("event_at"))
            vid = row.get("vendor_id")
            if not vid or vid.lower() in ("null", "none", ""):
                vid = None
                log_issue("call_attempts", row["attempt_id"], "MISSING_FIELD", "Attempt has missing vendor_id")

            attempt_rows.append({
                "attempt_id": row["attempt_id"],
                "call_id": row["call_id"],
                "account_id": row["account_id"],
                "borrower_id": row["borrower_id"],
                "agent_id": row.get("agent_id"),
                "attempt_no": int(row.get("attempt_no") or 1),
                "vendor_id": vid,
                "attempt_status": row.get("attempt_status", "UNKNOWN"),
                "event_at": ev_dt or datetime.now(timezone.utc)
            })
        fp.close()
        for i in range(0, len(attempt_rows), BATCH_SIZE):
            db.bulk_insert_mappings(m.CallAttempt, attempt_rows[i:i+BATCH_SIZE])
        db.commit()
        summary["tables"]["call_attempts"] = len(attempt_rows)

        # 10. Call Dispositions
        print("Ingesting call_dispositions & standardizing legacy codes...")
        fp, r = get_csv_reader("call_dispositions.csv")
        disp_rows = []
        for row in r:
            ev_dt = parse_and_normalize_timestamp(row.get("event_at"))
            canonical_code, raw_code = normalize_disposition_code(row.get("disposition_code"))
            if canonical_code != raw_code:
                log_issue("call_dispositions", row["disposition_id"], "LEGACY_CODE", f"Mapped legacy code {raw_code} -> {canonical_code}")

            disp_rows.append({
                "disposition_id": row["disposition_id"],
                "call_id": row["call_id"],
                "account_id": row["account_id"],
                "borrower_id": row["borrower_id"],
                "agent_id": row.get("agent_id"),
                "disposition_code": canonical_code,
                "raw_disposition_code": raw_code,
                "disposition_version": row.get("disposition_version"),
                "event_at": ev_dt or datetime.now(timezone.utc)
            })
        fp.close()
        for i in range(0, len(disp_rows), BATCH_SIZE):
            db.bulk_insert_mappings(m.CallDisposition, disp_rows[i:i+BATCH_SIZE])
        db.commit()
        summary["tables"]["call_dispositions"] = len(disp_rows)

        # 11. Agent Sessions
        print("Ingesting agent_sessions...")
        fp, r = get_csv_reader("agent_sessions.csv")
        session_rows = []
        for row in r:
            tz = row.get("timezone", "UTC")
            login_dt = parse_and_normalize_timestamp(row.get("login_at"), tz)
            logout_dt = parse_and_normalize_timestamp(row.get("logout_at"), tz)
            session_rows.append({
                "session_id": row["session_id"],
                "agent_id": row["agent_id"],
                "login_at": login_dt or datetime.now(timezone.utc),
                "logout_at": logout_dt,
                "channel": row.get("channel"),
                "device_id": row.get("device_id"),
                "timezone": tz
            })
        fp.close()
        for i in range(0, len(session_rows), BATCH_SIZE):
            db.bulk_insert_mappings(m.AgentSession, session_rows[i:i+BATCH_SIZE])
        db.commit()
        summary["tables"]["agent_sessions"] = len(session_rows)

        # 12. Payments
        print("Ingesting payments & deduplicating...")
        fp, r = get_csv_reader("payments.csv")
        payment_rows = []
        seen_payments = set()
        for row in r:
            pid = row["payment_id"]
            if pid in seen_payments:
                log_issue("payments", pid, "DUPLICATE_ROW", "Duplicate payment_id dropped")
                continue
            seen_payments.add(pid)
            ev_dt = parse_and_normalize_timestamp(row.get("event_at"))
            payment_rows.append({
                "payment_id": pid,
                "account_id": row["account_id"],
                "borrower_id": row["borrower_id"],
                "event_at": ev_dt or datetime.now(timezone.utc),
                "payment_reference": row.get("payment_reference"),
                "amount": float(row.get("amount") or 0.0),
                "payment_status": row.get("payment_status", "SUCCESS"),
                "payment_method": row.get("payment_method"),
                "provider_id": row.get("provider_id")
            })
        fp.close()
        for i in range(0, len(payment_rows), BATCH_SIZE):
            db.bulk_insert_mappings(m.Payment, payment_rows[i:i+BATCH_SIZE])
        db.commit()
        summary["tables"]["payments"] = len(payment_rows)

        # 13. Promises to Pay
        print("Ingesting promises_to_pay...")
        fp, r = get_csv_reader("promises_to_pay.csv")
        ptp_rows = []
        for row in r:
            ev_dt = parse_and_normalize_timestamp(row.get("event_at"))
            p_dt = parse_and_normalize_timestamp(row.get("promised_date"))
            ptp_rows.append({
                "ptp_id": row["ptp_id"],
                "account_id": row["account_id"],
                "borrower_id": row["borrower_id"],
                "event_at": ev_dt or datetime.now(timezone.utc),
                "agent_id": row.get("agent_id"),
                "promised_amount": float(row.get("promised_amount") or 0.0),
                "promised_date": p_dt,
                "status": row.get("status", "OPEN"),
                "source": row.get("source")
            })
        fp.close()
        for i in range(0, len(ptp_rows), BATCH_SIZE):
            db.bulk_insert_mappings(m.PromiseToPay, ptp_rows[i:i+BATCH_SIZE])
        db.commit()
        summary["tables"]["promises_to_pay"] = len(ptp_rows)

        # 14. Complaints
        print("Ingesting complaints...")
        fp, r = get_csv_reader("complaints.csv")
        complaint_rows = []
        for row in r:
            ev_dt = parse_and_normalize_timestamp(row.get("event_at"))
            res_dt = parse_and_normalize_timestamp(row.get("resolution_at"))
            complaint_rows.append({
                "complaint_id": row["complaint_id"],
                "account_id": row["account_id"],
                "borrower_id": row["borrower_id"],
                "event_at": ev_dt or datetime.now(timezone.utc),
                "complaint_type": row.get("complaint_type", "GENERAL"),
                "severity": row.get("severity", "MEDIUM"),
                "status": row.get("status", "OPEN"),
                "source": row.get("source"),
                "resolution_at": res_dt
            })
        fp.close()
        for i in range(0, len(complaint_rows), BATCH_SIZE):
            db.bulk_insert_mappings(m.Complaint, complaint_rows[i:i+BATCH_SIZE])
        db.commit()
        summary["tables"]["complaints"] = len(complaint_rows)

        # 15. Field Visits
        print("Ingesting field_visits...")
        fp, r = get_csv_reader("field_visits.csv")
        visit_rows = []
        for row in r:
            ev_dt = parse_and_normalize_timestamp(row.get("event_at"))
            sch_dt = parse_and_normalize_timestamp(row.get("scheduled_at"))
            visit_rows.append({
                "visit_id": row["visit_id"],
                "account_id": row["account_id"],
                "borrower_id": row["borrower_id"],
                "event_at": ev_dt or datetime.now(timezone.utc),
                "agent_id": row.get("agent_id"),
                "visit_type": row.get("visit_type", "FIRST_VISIT"),
                "outcome": row.get("outcome", "CONTACTED"),
                "latitude": float(row["latitude"]) if row.get("latitude") else None,
                "longitude": float(row["longitude"]) if row.get("longitude") else None,
                "scheduled_at": sch_dt
            })
        fp.close()
        for i in range(0, len(visit_rows), BATCH_SIZE):
            db.bulk_insert_mappings(m.FieldVisit, visit_rows[i:i+BATCH_SIZE])
        db.commit()
        summary["tables"]["field_visits"] = len(visit_rows)

        # 16. SMS Events
        print("Ingesting sms_events...")
        fp, r = get_csv_reader("sms_events.csv")
        sms_rows = []
        for row in r:
            ev_dt = parse_and_normalize_timestamp(row.get("event_at"))
            sms_rows.append({
                "sms_event_id": row["sms_event_id"],
                "account_id": row["account_id"],
                "borrower_id": row["borrower_id"],
                "event_at": ev_dt or datetime.now(timezone.utc),
                "message_id": row.get("message_id"),
                "event_type": row.get("event_type", "SENT"),
                "template_code": row.get("template_code"),
                "provider_id": row.get("provider_id")
            })
        fp.close()
        for i in range(0, len(sms_rows), BATCH_SIZE):
            db.bulk_insert_mappings(m.SmsEvent, sms_rows[i:i+BATCH_SIZE])
        db.commit()
        summary["tables"]["sms_events"] = len(sms_rows)

        # 17. WhatsApp Events
        print("Ingesting whatsapp_events & deduplicating...")
        fp, r = get_csv_reader("whatsapp_events.csv")
        wa_rows = []
        seen_wa = set()
        for row in r:
            wid = row["whatsapp_event_id"]
            if wid in seen_wa:
                log_issue("whatsapp_events", wid, "DUPLICATE_ROW", "Duplicate whatsapp_event_id dropped")
                continue
            seen_wa.add(wid)
            ev_dt = parse_and_normalize_timestamp(row.get("event_at"))
            wa_rows.append({
                "whatsapp_event_id": wid,
                "account_id": row["account_id"],
                "borrower_id": row["borrower_id"],
                "event_at": ev_dt or datetime.now(timezone.utc),
                "message_id": row.get("message_id"),
                "event_type": row.get("event_type", "SENT"),
                "template_code": row.get("template_code"),
                "provider_id": row.get("provider_id")
            })
        fp.close()
        for i in range(0, len(wa_rows), BATCH_SIZE):
            db.bulk_insert_mappings(m.WhatsappEvent, wa_rows[i:i+BATCH_SIZE])
        db.commit()
        summary["tables"]["whatsapp_events"] = len(wa_rows)

        # 18. Batch insert Ingestion Audit Logs
        print(f"Persisting {len(audit_logs)} ingestion audit logs...")
        for i in range(0, len(audit_logs), BATCH_SIZE):
            db.bulk_insert_mappings(m.IngestionAuditLog, audit_logs[i:i+BATCH_SIZE])
        db.commit()

        elapsed = time.time() - start_time
        summary["elapsed_seconds"] = round(elapsed, 2)
        summary["total_records_ingested"] = sum(summary["tables"].values())

        os.makedirs(SUMMARY_FILE.parent, exist_ok=True)
        with open(SUMMARY_FILE, "w") as out:
            json.dump(summary, out, indent=2)

        print("=" * 60)
        print(f"Ingestion completed successfully in {elapsed:.2f} seconds!")
        print(f"Total canonical records ingested: {summary['total_records_ingested']:,}")
        print("Table breakdown:")
        for t, cnt in summary["tables"].items():
            print(f"  {t:25}: {cnt:,}")
        print("Audit issues handled:")
        for k, v in summary["audit_issues"].items():
            print(f"  {k:25}: {v:,}")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"ERROR during ingestion: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_pipeline()
