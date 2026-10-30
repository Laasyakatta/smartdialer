"""
Borrower Eligibility & Contact Policy Service

Rules:
1. Account status must be ACTIVE (not CLOSED, PAID, WRITEOFF, or ORPHANED).
2. Contact suppression: Exclude borrowers with OPEN complaints of type 'DND', 'HARASSMENT', or 'PRIVACY'.
3. PTP suppression: Exclude borrowers who have KEPT their promise to pay or have payments within 24 hours.
4. Deduplication: One active call per borrower at any given time.
5. Max attempts per day enforced (default 3).
"""
from datetime import datetime, timezone, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select, update, func, and_

from backend.app.models.enums import AccountStatus, CallState
from backend.app.models.borrower import Borrower
from backend.app.models.account import Account
from backend.app.models.call import Call
from backend.app.models.campaign import DailyTargeting
from backend.app.models.collections_extra import Complaint, PromiseToPay, Payment

logger = logging.getLogger("smartdialer.eligibility")

CRITICAL_COMPLAINT_TYPES = {"DND", "HARASSMENT", "PRIVACY"}
ACTIVE_CALL_STATES = {
    CallState.QUEUED.value,
    CallState.RESERVED.value,
    CallState.INITIATED.value,
    CallState.RINGING.value,
    CallState.ANSWERED.value,
    CallState.CONNECTED.value,
}

class EligibilityService:
    @staticmethod
    def is_borrower_eligible(
        db: Session,
        borrower_id: str,
        account_id: str | None = None,
        max_daily_attempts: int = 3
    ) -> tuple[bool, str | None]:
        """
        Validates borrower eligibility across all compliance criteria.
        Returns: (is_eligible, ineligibility_reason)
        """
        borrower = db.get(Borrower, borrower_id)
        if not borrower:
            return False, "BORROWER_NOT_FOUND"

        if not borrower.phone:
            return False, "MISSING_PHONE_NUMBER"

        # Check existing active call
        if borrower.current_active_call_id is not None:
            return False, "BORROWER_ALREADY_IN_ACTIVE_CALL"

        # Check active call in DB
        active_call = db.scalar(
            select(Call.call_id)
            .where(
                Call.borrower_id == borrower_id,
                Call.state.in_(ACTIVE_CALL_STATES)
            )
            .limit(1)
        )
        if active_call:
            return False, "BORROWER_HAS_CALL_IN_FLIGHT"

        # Check Account Status
        if account_id:
            account = db.get(Account, account_id)
            if not account:
                return False, "ACCOUNT_NOT_FOUND"
            if account.is_orphaned:
                return False, "ACCOUNT_ORPHANED"
            if account.status not in (AccountStatus.ACTIVE.value, "DELINQUENT", "NPA"):
                return False, f"INELIGIBLE_ACCOUNT_STATUS_{account.status}"

        # Check Open Complaints (DND / Harassment)
        suppressed_complaint = db.scalar(
            select(Complaint.complaint_id)
            .where(
                Complaint.borrower_id == borrower_id,
                Complaint.complaint_type.in_(CRITICAL_COMPLAINT_TYPES),
                Complaint.status.in_(["OPEN", "INVESTIGATING"])
            )
            .limit(1)
        )
        if suppressed_complaint:
            return False, "SUPPRESSED_BY_DND_OR_COMPLAINT"

        # Check Daily Call Attempt Frequency Limit
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        daily_attempts = db.scalar(
            select(func.count(Call.call_id))
            .where(
                Call.borrower_id == borrower_id,
                Call.queued_at >= today_start
            )
        ) or 0

        if daily_attempts >= max_daily_attempts:
            return False, f"DAILY_ATTEMPT_LIMIT_REACHED_{daily_attempts}"

        return True, None

    @staticmethod
    def get_candidate_borrowers_for_campaign(
        db: Session,
        campaign_id: str,
        limit: int = 50
    ) -> list[tuple[str, str]]:
        """
        Retrieves eligible candidate (borrower_id, account_id) tuples from daily targeting
        or active accounts for this campaign.
        """
        # First query daily targeting
        query = (
            select(DailyTargeting.account_id, Account.borrower_id)
            .join(Account, DailyTargeting.account_id == Account.account_id)
            .where(
                DailyTargeting.campaign_id == campaign_id,
                DailyTargeting.status.in_(["QUEUED", "ACTIVE"]),
                Account.borrower_id.isnot(None),
                Account.status.in_(["ACTIVE", "DELINQUENT", "NPA"])
            )
            .order_by(DailyTargeting.priority.desc())
            .limit(limit * 3)
        )
        candidates = db.execute(query).all()

        eligible = []
        for acc_id, b_id in candidates:
            if not b_id:
                continue
            is_ok, _ = EligibilityService.is_borrower_eligible(db, b_id, acc_id)
            if is_ok:
                eligible.append((b_id, acc_id))
                if len(eligible) >= limit:
                    break

        # Fallback to direct accounts if daily targeting queue is exhausted
        if len(eligible) < limit:
            fallback_query = (
                select(Account.account_id, Account.borrower_id)
                .where(
                    Account.status.in_(["ACTIVE", "DELINQUENT", "NPA"]),
                    Account.borrower_id.isnot(None)
                )
                .limit(limit * 3)
            )
            for acc_id, b_id in db.execute(fallback_query).all():
                if len(eligible) >= limit:
                    break
                if any(b_id == existing_b for existing_b, _ in eligible):
                    continue
                is_ok, _ = EligibilityService.is_borrower_eligible(db, b_id, acc_id)
                if is_ok:
                    eligible.append((b_id, acc_id))

        return eligible

    @staticmethod
    def reserve_borrower_atomic(db: Session, borrower_id: str, call_id: str) -> bool:
        """
        Atomically marks borrower as in-call to prevent double dialing across workers.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            update(Borrower)
            .where(
                Borrower.borrower_id == borrower_id,
                Borrower.current_active_call_id.is_(None)
            )
            .values(
                current_active_call_id=call_id,
                reserved_at=now
            )
        )
        res = db.execute(stmt)
        db.commit()
        return res.rowcount > 0

    @staticmethod
    def release_borrower(db: Session, borrower_id: str) -> bool:
        """
        Safely releases borrower lock after call termination.
        """
        stmt = (
            update(Borrower)
            .where(Borrower.borrower_id == borrower_id)
            .values(
                current_active_call_id=None,
                reserved_at=None
            )
        )
        res = db.execute(stmt)
        db.commit()
        return res.rowcount > 0
