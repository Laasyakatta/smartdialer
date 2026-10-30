"""
Borrower Management API Router (with PII Masking)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from backend.app.core.database import get_db
from backend.app.models.borrower import Borrower
from backend.app.core.security import mask_phone, mask_email

router = APIRouter(prefix="/borrowers", tags=["borrowers"])

@router.get("")
def list_borrowers(
    eligible_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = select(Borrower)
    if eligible_only:
        query = query.where(Borrower.is_eligible.is_(True))

    total = db.scalar(
        select(func.count(Borrower.borrower_id))
        .where(Borrower.is_eligible.is_(True) if eligible_only else True)
    ) or 0

    borrowers = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "borrower_id": b.borrower_id,
                "name": b.name,
                "phone_masked": mask_phone(b.phone),
                "email_masked": mask_email(b.email),
                "city": b.city,
                "state": b.state,
                "is_eligible": b.is_eligible,
                "ineligibility_reason": b.ineligibility_reason,
                "current_active_call_id": b.current_active_call_id
            }
            for b in borrowers
        ]
    }
