"""
Borrower Eligibility & Contact Policy Tests
"""
from backend.app.models.borrower import Borrower
from backend.app.models.account import Account
from backend.app.models.collections_extra import Complaint
from backend.app.services.eligibility_service import EligibilityService
from backend.app.core.security import mask_phone, mask_email

def test_borrower_eligibility_criteria(test_db):
    # 1. Normal active borrower
    test_db.add(Borrower(borrower_id="BRW_EL_1", name="Eligible Bob", phone="9876543210", is_eligible=True))
    test_db.add(Account(account_id="ACC_EL_1", borrower_id="BRW_EL_1", status="ACTIVE"))

    # 2. Borrower on CLOSED account
    test_db.add(Borrower(borrower_id="BRW_EL_2", name="Closed Acct Bob", phone="9876543211", is_eligible=True))
    test_db.add(Account(account_id="ACC_EL_2", borrower_id="BRW_EL_2", status="CLOSED"))

    # 3. Borrower with DND complaint
    test_db.add(Borrower(borrower_id="BRW_EL_3", name="DND Bob", phone="9876543212", is_eligible=True))
    test_db.add(Account(account_id="ACC_EL_3", borrower_id="BRW_EL_3", status="ACTIVE"))
    test_db.add(Complaint(
        complaint_id="CMPL_1",
        account_id="ACC_EL_3",
        borrower_id="BRW_EL_3",
        complaint_type="DND",
        status="OPEN",
        severity="HIGH",
        event_at=None
    ))
    test_db.commit()

    # Verify BRW_EL_1 is eligible
    ok1, reason1 = EligibilityService.is_borrower_eligible(test_db, "BRW_EL_1", "ACC_EL_1")
    assert ok1 is True
    assert reason1 is None

    # Verify BRW_EL_2 is ineligible due to CLOSED account
    ok2, reason2 = EligibilityService.is_borrower_eligible(test_db, "BRW_EL_2", "ACC_EL_2")
    assert ok2 is False
    assert "CLOSED" in reason2

    # Verify BRW_EL_3 is ineligible due to DND complaint
    ok3, reason3 = EligibilityService.is_borrower_eligible(test_db, "BRW_EL_3", "ACC_EL_3")
    assert ok3 is False
    assert reason3 == "SUPPRESSED_BY_DND_OR_COMPLAINT"

def test_pii_masking():
    assert mask_phone("9912497306") == "99****7306"
    assert mask_phone(None) == "N/A"
    assert mask_email("user8943@example.com") == "u******3@example.com"
    assert mask_email(None) == "N/A"
