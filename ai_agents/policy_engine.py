import hashlib
import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional

import pypdfium2  # type: ignore

from claims.models import Claim

POLICY_LIMITS = {
    "flight": {"approve": 12000, "review": 20000, "reject": 20000},
    "hotel": {"approve": 6000, "review": 12000, "reject": 15000},
    "food": {"approve": 2000, "review": 3000, "reject": 4000},
    "taxi": {"approve": 1000, "review": 1500, "reject": 2000},
}

def _normalize_text(value: str) -> str:
    return (value or "").lower().strip()


def _expense_type_from_title(title: str) -> Optional[str]:
    text = _normalize_text(title)

    if "flight" in text:
        return "flight"
    if "hotel" in text:
        return "hotel"
    if "food" in text or "meal" in text or "restaurant" in text:
        return "food"
    if "taxi" in text or "cab" in text or "uber" in text or "ola" in text:
        return "taxi"
    return None


def _coerce_decimal(value: Any) -> Optional[Decimal]:
    if value in [None, "", False]:
        return None

    try:
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _extract_receipt_amount(value: Any) -> Optional[Decimal]:
    if value in [None, "", False]:
        return None

    if isinstance(value, (Decimal, int, float)):
        return _coerce_decimal(value)

    if hasattr(value, "read"):
        try:
            if hasattr(value, "seek"):
                value.seek(0)
            raw_bytes = value.read()
            if hasattr(value, "seek"):
                value.seek(0)
        except Exception:
            return None
    else:
        raw_bytes = value if isinstance(value, (bytes, bytearray)) else None

    if not raw_bytes:
        return None

    name = None
    if hasattr(value, "name"):
        name = str(value.name).lower()
    elif isinstance(value, (bytes, bytearray)):
        name = ""

    if name.endswith(".pdf") or raw_bytes.startswith(b"%PDF"):
        try:
            pdf = pypdfium2.PdfDocument(raw_bytes)
            text_parts = []
            for page in pdf:
                text = page.get_textpage().get_text()
                if text:
                    text_parts.append(text)
            combined_text = "\n".join(text_parts)
            if combined_text:
                amount_candidates = []
                for line in combined_text.replace("\n", " ").split():
                    cleaned = line.strip("$₹.,")
                    if cleaned.isdigit() or cleaned.replace(".", "", 1).isdigit():
                        amount_candidates.append(cleaned)
                if amount_candidates:
                    for candidate in reversed(amount_candidates):
                        try:
                            return Decimal(candidate)
                        except InvalidOperation:
                            continue
        except Exception:
            pass

    text = raw_bytes.decode("utf-8", errors="ignore") if isinstance(raw_bytes, (bytes, bytearray)) else str(raw_bytes)
    if not text:
        return None

    normalized_text = text.replace("\n", " ").replace("\r", " ")
    lower_text = normalized_text.lower()

    for marker in ["invoice total", "total", "grand total", "subtotal", "net total", "amount due"]:
        if marker in lower_text:
            pattern = re.compile(rf"(?:{re.escape(marker)})[^\d$₹]*(\d+(?:[.,]\d{{1,2}})?)")
            match = pattern.search(lower_text)
            if match:
                candidate = match.group(1).replace(",", "")
                try:
                    return Decimal(candidate)
                except InvalidOperation:
                    continue

    for token in normalized_text.replace(",", " ").split():
        cleaned = token.strip("$₹.,")
        if not cleaned.isdigit() and not (cleaned.replace(".", "", 1).isdigit()):
            continue
        try:
            value = Decimal(cleaned)
        except InvalidOperation:
            continue
        if value <= 0:
            continue
        return value

    return None


def _invoice_match_status(claim: Any) -> Dict[str, Any]:
    entered_amount = _coerce_decimal(getattr(claim, "amount", 0) or 0)
    if entered_amount is None:
        entered_amount = Decimal("0")

    invoice_amount = None
    for field_name in ["invoice_total", "invoice_amount", "invoice_sum", "invoice_value"]:
        if hasattr(claim, field_name):
            value = getattr(claim, field_name)
            if value not in [None, ""]:
                invoice_amount = _coerce_decimal(value)
                if invoice_amount is not None:
                    break

    if invoice_amount is None and hasattr(claim, "invoice"):
        invoice_amount = _extract_receipt_amount(getattr(claim, "invoice", None))

    if invoice_amount is None:
        return {
            "matched": True,
            "violation": False,
            "flag": None,
            "invoice_amount": None,
        }

    matched = abs(entered_amount - invoice_amount) < Decimal("0.01")
    return {
        "matched": matched,
        "violation": not matched,
        "flag": None if matched else f"Invoice total mismatch: entered {entered_amount} vs invoice {invoice_amount}",
        "invoice_amount": invoice_amount,
        "entered_amount": entered_amount,
    }


def _get_invoice_identity(invoice: Any) -> Dict[str, Optional[str]]:
    if invoice in [None, ""]:
        return {"name": None, "signature": None}

    name = None
    signature = None

    if hasattr(invoice, "name"):
        name = str(invoice.name)
    elif hasattr(invoice, "file") and hasattr(invoice.file, "name"):
        name = str(invoice.file.name)
    else:
        name = str(invoice)

    try:
        if hasattr(invoice, "read"):
            if hasattr(invoice, "seek"):
                invoice.seek(0)
            payload = invoice.read()
            if hasattr(invoice, "seek"):
                invoice.seek(0)
            if payload is not None:
                signature = hashlib.sha256(payload).hexdigest()
        elif hasattr(invoice, "open"):
            with invoice.open("rb") as handle:
                signature = hashlib.sha256(handle.read()).hexdigest()
        elif isinstance(invoice, (bytes, bytearray)):
            signature = hashlib.sha256(invoice).hexdigest()
    except Exception:
        signature = None

    return {
        "name": os.path.basename(name) if name else None,
        "signature": signature,
    }


def _duplicate_receipt_status(claim: Any) -> Dict[str, Any]:
    employee = getattr(claim, "employee", None)
    if not employee:
        return {"duplicate": False, "flag": None}

    invoice = getattr(claim, "invoice", None)
    if invoice in [None, ""]:
        return {"duplicate": False, "flag": None}

    try:
        existing_claims = Claim.objects.filter(employee=employee)
    except Exception:
        return {"duplicate": False, "flag": None}

    current_identity = _get_invoice_identity(invoice)
    candidate_name = current_identity["name"]
    candidate_signature = current_identity["signature"]

    for existing_claim in existing_claims.exclude(id=getattr(claim, "id", None)):
        existing_invoice = getattr(existing_claim, "invoice", None)
        if not existing_invoice:
            continue

        existing_identity = _get_invoice_identity(existing_invoice)
        existing_name = existing_identity["name"]
        existing_signature = existing_identity["signature"]

        same_name = bool(candidate_name and existing_name and candidate_name == existing_name)
        same_signature = bool(candidate_signature and existing_signature and candidate_signature == existing_signature)

        if same_name or same_signature:
            return {
                "duplicate": True,
                "flag": "Duplicate receipt detected for this employee; manual review required",
            }

    return {"duplicate": False, "flag": None}


def _weekend_flag(claim: Any) -> Optional[str]:
    created_at = getattr(claim, "created_at", None)

    if isinstance(created_at, str):
        try:
            created_at = datetime.fromisoformat(created_at)
        except Exception:
            return None

    if created_at and hasattr(created_at, "weekday") and created_at.weekday() >= 5:
        return "Weekend claim submission detected"

    return None


def _memory_risk(employee_history: Dict[str, Any]) -> Dict[str, Any]:
    total_claims = int(employee_history.get("total_claims", 0) or 0)
    avg_amount = float(employee_history.get("avg_amount", 0) or 0)
    high_value_count = int(employee_history.get("high_value_count", 0) or 0)
    duplicate_invoice = bool(employee_history.get("duplicate_invoice", False))
    is_first_claim = bool(employee_history.get("is_first_claim", total_claims == 1))

    flags = []
    risk_points = 0

    if duplicate_invoice:
        flags.append("Duplicate invoice detected in employee memory")
        risk_points += 4

    if total_claims > 25:
        flags.append("Very high claim frequency")
        risk_points += 2
    elif total_claims > 10:
        flags.append("Moderate claim frequency")
        risk_points += 1

    if high_value_count > 5:
        flags.append("Repeated high-value claims")
        risk_points += 1

    if avg_amount > 0 and avg_amount > 10000 and total_claims >= 3:
        flags.append("High average claim value")
        risk_points += 1

    if is_first_claim:
        flags.append("First claim detected")
        risk_points = max(0, risk_points - 1)

    if risk_points >= 4:
        level = "HIGH"
    elif risk_points >= 2:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "risk_points": risk_points,
        "risk_level": level,
        "flags": flags,
        "is_first_claim": is_first_claim,
    }


def policy_engine(claim, employee_history=None):
    if employee_history is None:
        employee_history = {}

    title = _normalize_text(getattr(claim, "title", ""))
    amount = float(getattr(claim, "amount", 0) or 0)

    flags = []
    violation = False
    decision = "APPROVE"

    expense_type = _expense_type_from_title(title)

    # Any amount over the approve limit → REJECT immediately
    if expense_type in POLICY_LIMITS:
        limits = POLICY_LIMITS[expense_type]
        if amount > limits["approve"]:
            flags.append(f"{expense_type.title()} claim exceeds policy limit of ₹{limits['approve']}")
            decision = "REJECT"
            violation = True

    # Amount mismatch is no longer treated as a blocking policy violation.
    duplicate_check = _duplicate_receipt_status(claim)
    if duplicate_check["duplicate"]:
        flags.append(duplicate_check["flag"])
        if decision != "REJECT":
            decision = "MANUAL_REVIEW"
        violation = True

    # Weekend submission → REJECT
    weekend_flag = _weekend_flag(claim)
    if weekend_flag:
        flags.append(weekend_flag)
        if decision not in ("REJECT",):
            decision = "REJECT"
        violation = True

    mem = _memory_risk(employee_history)
    if mem["flags"]:
        flags.extend(mem["flags"])

    # HIGH memory risk → REJECT
    if mem["risk_level"] == "HIGH":
        if decision == "APPROVE":
            decision = "REJECT"
            violation = True

    return {
        "decision": decision,
        "flags": flags,
        "violation": violation,
        "reason": " | ".join(flags) if flags else "No violations detected",
        "action": "REJECT" if decision == "REJECT" else ("MANUAL_REVIEW" if decision == "MANUAL_REVIEW" else "APPROVE"),
        "expense_type": expense_type,
        "memory_risk_level": mem["risk_level"],
        "is_first_claim": mem["is_first_claim"],
    }


def check_policy(employee_id, title, amount, invoice_amount=None, claim_date=None, employee_history=None):
    if employee_history is None:
        employee_history = {}

    title = _normalize_text(title)
    amount = float(amount or 0)

    flags = []
    risk_level = "LOW"
    violation = False

    expense_type = _expense_type_from_title(title)

    # Any amount over approve limit → HIGH risk (triggers REJECT in claim_analyzer)
    if expense_type in POLICY_LIMITS:
        limits = POLICY_LIMITS[expense_type]
        if amount > limits["approve"]:
            flags.append(f"{expense_type.title()} claim exceeds policy limit of ₹{limits['approve']}")
            violation = True
            risk_level = "HIGH"

    # Invoice mismatch → MEDIUM risk (triggers MANUAL_REVIEW in claim_analyzer)
    if invoice_amount is not None:
        try:
            invoice_amount = float(invoice_amount)
            if abs(amount - invoice_amount) >= 0.01:
                flags.append(f"Invoice total mismatch: entered amount {amount} does not match invoice amount {invoice_amount}")
                violation = True
                if risk_level == "LOW":
                    risk_level = "MEDIUM"
        except Exception:
            pass

    # Weekend submission → HIGH risk (triggers REJECT in claim_analyzer)
    if claim_date is not None:
        try:
            if isinstance(claim_date, str):
                claim_date = datetime.fromisoformat(claim_date)
            if hasattr(claim_date, "weekday") and claim_date.weekday() >= 5:
                flags.append("Weekend claim submission detected")
                violation = True
                if risk_level != "HIGH":
                    risk_level = "HIGH"
        except Exception:
            pass

    mem = _memory_risk(employee_history)
    if mem["flags"]:
        flags.extend(mem["flags"])

    if mem["risk_level"] == "HIGH":
        if risk_level == "LOW":
            risk_level = "MEDIUM"
    elif mem["risk_level"] == "MEDIUM":
        if risk_level == "LOW":
            risk_level = "LOW"

    return {
        "violation": violation,
        "risk_level": risk_level,
        "flags": flags,
        "reason": " | ".join(flags) if flags else "No violations detected",
        "expense_type": expense_type,
        "is_first_claim": mem["is_first_claim"],
    }
