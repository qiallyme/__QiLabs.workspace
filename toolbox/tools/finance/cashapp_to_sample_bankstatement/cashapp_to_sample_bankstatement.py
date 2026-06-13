#!/usr/bin/env python3
# file: cashapp_to_sample_bankstatement.py
# purpose: Toolbox tool module for Cashapp To Sample Bankstatement. Provides tool class for the QiOne Desktop Tools UI.
# usage: Loaded by the QiOne toolbox build system and launched from main_ui.py.
# inputs: User-selected target directory and tool-specific UI options.
# outputs: Tool-specific logs, generated files, or file operations depending on selected mode.
# safety: Supports scan/dry-run vs live execution through the QiOne toolbox shell when implemented by the tool.
# owner: QiLabs

"""
Convert a Cash App export CSV into a simple bank-statement-style CSV with columns:
Date, Withdrawals, Deposits, Payee, Description, Reference Number

Usage:
    python cashapp_to_sample_bankstatement.py input.csv output.csv
    python cashapp_to_sample_bankstatement.py input.csv output.csv --description-max 120
    python cashapp_to_sample_bankstatement.py input.csv output.csv --include-failed --include-zero
"""

from __future__ import annotations

import argparse
import csv
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, Iterable, Optional

TARGET_HEADERS = [
    "Date",
    "Withdrawals",
    "Deposits",
    "Payee",
    "Description",
    "Reference Number",
]

TZ_SUFFIX_RE = re.compile(r"\s+[A-Z]{2,5}$")
MULTISPACE_RE = re.compile(r"\s+")


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return ""
    return MULTISPACE_RE.sub(" ", text)


def parse_money(value: object) -> Decimal:
    text = clean_text(value)
    if not text:
        return Decimal("0.00")

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]

    text = text.replace(",", "").replace("$", "").strip()

    if text.startswith("-"):
        negative = True
        text = text[1:].strip()
    elif text.startswith("+"):
        text = text[1:].strip()

    if not text:
        return Decimal("0.00")

    try:
        amount = Decimal(text)
    except InvalidOperation:
        return Decimal("0.00")

    if negative:
        amount *= Decimal("-1")

    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def format_money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"


def normalize_date(value: object) -> str:
    text = clean_text(value)
    if not text:
        return ""

    stripped = TZ_SUFFIX_RE.sub("", text)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(stripped, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Fallback: if it starts with ISO date, keep that.
    if len(text) >= 10 and re.match(r"\d{4}-\d{2}-\d{2}", text[:10]):
        return text[:10]
    return text


def truncate_text(text: str, max_len: int) -> str:
    text = clean_text(text)
    if max_len <= 0 or len(text) <= max_len:
        return text
    if max_len <= 3:
        return text[:max_len]
    return text[: max_len - 3].rstrip() + "..."


def merchant_from_note(note: str) -> str:
    merchant = clean_text(note)
    if not merchant:
        return ""

    # Cash App Pay pattern: "$19.52 Payment At DoorDash" -> "DoorDash"
    merchant = re.sub(r"^\$?[\d,]+(?:\.\d{2})?\s+Payment\s+At\s+", "", merchant, flags=re.I)

    # Common card authorization prefixes.
    merchant = re.sub(r"^[A-Z]{2,6}\s*\*+\s*", "", merchant)  # DD *MERCHANT
    merchant = re.sub(r"^[A-Z]{1,6}#\d+", "", merchant)        # BP#2084000MERCHANT
    merchant = re.sub(r"^[A-Z]{2,6}/", "", merchant)            # SHELL/SHELL -> SHELL

    merchant = merchant.strip(" -:/*")
    merchant = MULTISPACE_RE.sub(" ", merchant)
    return merchant


def build_payee(row: Dict[str, str]) -> str:
    counterparty = clean_text(row.get("Name of sender/receiver"))
    if counterparty:
        return counterparty

    note = clean_text(row.get("Notes"))
    tx_type = clean_text(row.get("Transaction Type"))
    account = clean_text(row.get("Account"))

    internal_notes = {
        "Cash Out",
        "Add Cash",
        "repayment",
        "non-repayment update",
        "Savings",
        "Borrowing in Cash App",
        "New device login",
    }
    internal_types = {
        "Deposits",
        "Withdrawal",
        "Savings Internal Transfer",
        "Overdraft",
        "Borrow",
        "Account Notifications",
        "Savings Interest Payment",
    }

    if note in internal_notes or tx_type in internal_types:
        if account and account.lower() != "cash balance":
            return account
        return "Cash App"

    merchant = merchant_from_note(note)
    if merchant:
        return merchant

    if account and account.lower() != "cash balance":
        return account

    return "Cash App"


def build_description(row: Dict[str, str], max_len: int) -> str:
    note = clean_text(row.get("Notes"))
    tx_type = clean_text(row.get("Transaction Type"))
    status = clean_text(row.get("Status"))
    account = clean_text(row.get("Account"))
    fee = parse_money(row.get("Fee"))
    currency = clean_text(row.get("Currency"))

    parts = []
    if note:
        parts.append(note)
    if tx_type:
        parts.append(f"type={tx_type}")
    if account:
        parts.append(f"account={account}")
    if fee != Decimal("0.00"):
        parts.append(f"fee={format_money(abs(fee))}")
    if status and status.upper() != "COMPLETE":
        parts.append(f"status={status}")
    if currency and currency.upper() != "USD":
        parts.append(f"currency={currency}")

    description = "; ".join(parts)
    return truncate_text(description, max_len)


def pick_effective_amount(row: Dict[str, str]) -> Decimal:
    net_amount = parse_money(row.get("Net Amount"))
    gross_amount = parse_money(row.get("Amount"))
    return net_amount if net_amount != Decimal("0.00") else gross_amount


def transform_rows(
    rows: Iterable[Dict[str, str]],
    description_max: int,
    include_failed: bool,
    include_zero: bool,
) -> Iterable[Dict[str, str]]:
    for row in rows:
        status = clean_text(row.get("Status"))
        amount = pick_effective_amount(row)

        if not include_failed and status and status.upper() != "COMPLETE":
            continue
        if not include_zero and amount == Decimal("0.00"):
            continue

        withdrawal = Decimal("0.00")
        deposit = Decimal("0.00")
        if amount < 0:
            withdrawal = abs(amount)
        elif amount > 0:
            deposit = amount

        yield {
            "Date": normalize_date(row.get("Date")),
            "Withdrawals": format_money(withdrawal),
            "Deposits": format_money(deposit),
            "Payee": build_payee(row),
            "Description": build_description(row, description_max),
            "Reference Number": clean_text(row.get("Transaction ID")),
        }


def convert_file(
    input_path: Path,
    output_path: Path,
    description_max: int = 120,
    include_failed: bool = False,
    include_zero: bool = False,
) -> None:
    with input_path.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        rows = list(reader)

    converted = list(
        transform_rows(
            rows,
            description_max=description_max,
            include_failed=include_failed,
            include_zero=include_zero,
        )
    )

    with output_path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=TARGET_HEADERS)
        writer.writeheader()
        writer.writerows(converted)



def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a Cash App CSV export into the sample bank statement layout."
    )
    parser.add_argument("input_csv", help="Path to the Cash App CSV export")
    parser.add_argument("output_csv", help="Path to write the converted CSV")
    parser.add_argument(
        "--description-max",
        type=int,
        default=120,
        help="Maximum character count for the Description column (default: 120)",
    )
    parser.add_argument(
        "--include-failed",
        action="store_true",
        help="Keep non-COMPLETE transactions instead of filtering them out",
    )
    parser.add_argument(
        "--include-zero",
        action="store_true",
        help="Keep $0.00 rows such as notifications",
    )

    args = parser.parse_args()
    convert_file(
        input_path=Path(args.input_csv),
        output_path=Path(args.output_csv),
        description_max=args.description_max,
        include_failed=args.include_failed,
        include_zero=args.include_zero,
    )


if __name__ == "__main__":
    main()
