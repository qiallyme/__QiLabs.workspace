from __future__ import annotations

import os
import tkinter as tk
from datetime import datetime
from tkinter import ttk

from core.base_tool import BaseTool


LEDGER_ACCOUNT = "Zaitullah Jan Ledger"
INCREASE_SOURCE = "Zai Ledger Increases"
DECREASE_DESTINATION = "Zai Ledger Decreases"

RAW_TRANSACTIONS = [
    {"trans_id": "TRANS-3", "date": "1-Dec-24", "description": "Balance Forward", "debit": "5570.00", "credit": "0.00", "balance": "5570", "bank_fee": "0.00", "balance_after_fees": "5570.00", "category": "Multiple", "notes": "Honda Accident and backed rent payments"},
    {"trans_id": "TRANS-9", "date": "1-Dec-24", "description": "For Food Cody", "debit": "0.00", "credit": "10.00", "balance": "-10", "bank_fee": "0.00", "balance_after_fees": "-10.00", "category": "Rent Payment", "notes": ""},
    {"trans_id": "TRANS-10", "date": "1-Dec-24", "description": "Cash Withdrawal", "debit": "0.00", "credit": "188.99", "balance": "-188.99", "bank_fee": "-6.76", "balance_after_fees": "-182.23", "category": "Transfer", "notes": ""},
    {"trans_id": "TRANS-16", "date": "1-Dec-24", "description": "Ledger Adjustment", "debit": "98.55", "credit": "0.00", "balance": "98.55", "bank_fee": "0.00", "balance_after_fees": "98.55", "category": "Transfer", "notes": ""},
    {"trans_id": "TRANS-14", "date": "3-Dec-24", "description": "Ledger Adjustment", "debit": "50.00", "credit": "58.05", "balance": "-8.05", "bank_fee": "0.00", "balance_after_fees": "-8.05", "category": "Entertainment-Kriko", "notes": ""},
    {"trans_id": "TRANS-15", "date": "3-Dec-24", "description": "Ledger Adjustment", "debit": "0.00", "credit": "1.45", "balance": "-1.45", "bank_fee": "0.00", "balance_after_fees": "-1.45", "category": "Transfer", "notes": ""},
    {"trans_id": "TRANS-11", "date": "5-Dec-24", "description": "Ledger Adjustment", "debit": "0.00", "credit": "5.00", "balance": "-5", "bank_fee": "0.23", "balance_after_fees": "-5.23", "category": "Rent Payment", "notes": ""},
    {"trans_id": "TRANS-12", "date": "5-Dec-24", "description": "Ledger Adjustment", "debit": "0.00", "credit": "82.00", "balance": "-82", "bank_fee": "2.23", "balance_after_fees": "-84.23", "category": "Uncategorized", "notes": ""},
    {"trans_id": "TRANS-13", "date": "5-Dec-24", "description": "Ledger Adjustment", "debit": "0.00", "credit": "50.00", "balance": "-50", "bank_fee": "1.40", "balance_after_fees": "-51.40", "category": "Uncategorized", "notes": ""},
    {"trans_id": "TRANS-1", "date": "7-Dec-24", "description": "Kriko Entertainment-Gifts", "debit": "0.00", "credit": "16.00", "balance": "-16", "bank_fee": "0.00", "balance_after_fees": "-16.00", "category": "Entertainment-Kriko", "notes": "Provided a portion from the original purchase of $50.00; still need to provide the other $34.00."},
    {"trans_id": "TRANS-4", "date": "10-Dec-24", "description": "Entertainment-Gifts", "debit": "138.00", "credit": "0.00", "balance": "138", "bank_fee": "4.98", "balance_after_fees": "133.02", "category": "Entertainment-Kriko", "notes": "60 for one listed 40 for the difference gets a little over 1/2 .68"},
    {"trans_id": "TRANS-5", "date": "10-Dec-24", "description": "Entertainment-Gifts", "debit": "14.00", "credit": "0.00", "balance": "14", "bank_fee": "0.00", "balance_after_fees": "14.00", "category": "Entertainment-Kriko", "notes": "Owed one gram"},
    {"trans_id": "TRANS-6", "date": "10-Dec-24", "description": "Tesla Charger", "debit": "0.00", "credit": "21.00", "balance": "-21", "bank_fee": "0.00", "balance_after_fees": "-21.00", "category": "Fuel", "notes": "n/a"},
    {"trans_id": "TRANS-7", "date": "10-Dec-24", "description": "Tesla Charger", "debit": "0.00", "credit": "50.00", "balance": "-50", "bank_fee": "0.00", "balance_after_fees": "-50.00", "category": "Rent Payment", "notes": "n/a"},
    {"trans_id": "TRANS-8", "date": "10-Dec-24", "description": "For Food", "debit": "40.00", "credit": "0.00", "balance": "40", "bank_fee": "0.20", "balance_after_fees": "39.80", "category": "Entertainment-Kriko", "notes": "n/a"},
]


class ZaiLedgerImporterTool(BaseTool):
    def __init__(self):
        self.cancel_requested = False
        self.url_var = None
        self.token_var = None

    def get_name(self):
        return "Zai Ledger Importer"

    def build_ui(self, parent):
        ttk.Label(parent, text="Import the bundled Zai ledger transactions into Firefly III.", background="#121a2b", foreground="white").pack(anchor="w", pady=(0, 10))

        self.url_var = tk.StringVar(value=os.environ.get("FIREFLY_URL", ""))
        self.token_var = tk.StringVar(value="")

        ttk.Label(parent, text="Firefly URL (blank = FIREFLY_URL env var)", background="#121a2b", foreground="white").pack(anchor="w", pady=(0, 4))
        tk.Entry(parent, textvariable=self.url_var, bg="#10192a", fg="white", insertbackground="white", relief="flat").pack(fill="x", ipady=6, pady=(0, 10))

        ttk.Label(parent, text="Access token (blank = FIREFLY_TOKEN env var)", background="#121a2b", foreground="white").pack(anchor="w", pady=(0, 4))
        tk.Entry(parent, textvariable=self.token_var, bg="#10192a", fg="white", insertbackground="white", relief="flat", show="*").pack(fill="x", ipady=6, pady=(0, 10))

        ttk.Label(parent, text=f"Bundled transactions: {len(RAW_TRANSACTIONS)}", background="#121a2b", foreground="#8ea2c7").pack(anchor="w")

    def resolve_credentials(self):
        url = (self.url_var.get().strip() or os.environ.get("FIREFLY_URL", "")).rstrip("/")
        token = self.token_var.get().strip() or os.environ.get("FIREFLY_TOKEN", "")
        return url, token

    def parse_money(self, value):
        value = str(value).replace("$", "").replace(",", "").replace("(", "-").replace(")", "").strip()
        return 0.0 if value == "" else round(float(value), 2)

    def parse_date(self, value):
        return datetime.strptime(value, "%d-%b-%y").date().isoformat()

    def build_payload(self, record):
        debit = self.parse_money(record["debit"])
        credit = self.parse_money(record["credit"])
        net = round(debit - credit, 2)
        if net == 0:
            return None

        if net > 0:
            tx_type = "deposit"
            source_name = INCREASE_SOURCE
            destination_name = LEDGER_ACCOUNT
            direction_note = "Positive ledger movement: increases amount Zaitullah Jan owes Cody/household."
        else:
            tx_type = "withdrawal"
            source_name = LEDGER_ACCOUNT
            destination_name = DECREASE_DESTINATION
            direction_note = "Negative ledger movement: decreases amount Zaitullah Jan owes or creates credit in his favor."

        amount = abs(net)
        description = record["description"].strip() or f"Zai Ledger {record['trans_id']}"
        notes = (
            "# Zaitullah Jan Ledger Import\n\n"
            f"Transaction ID: {record['trans_id']}\n"
            f"Original Date: {record['date']}\n"
            f"Original Description: {record['description']}\n"
            f"Original Debit (+): {record['debit']}\n"
            f"Original Credit (-): {record['credit']}\n"
            f"Original Balance: {record['balance']}\n"
            f"Bank Fee: {record['bank_fee']}\n"
            f"Balance After Fees: {record['balance_after_fees']}\n"
            f"Original Category: {record['category']}\n\n"
            f"Ledger Interpretation: {direction_note}\n\n"
            f"Original Notes:\n{record['notes']}\n"
        )

        return {
            "error_if_duplicate_hash": False,
            "apply_rules": False,
            "transactions": [
                {
                    "type": tx_type,
                    "date": self.parse_date(record["date"]),
                    "amount": f"{amount:.2f}",
                    "description": f"Zai Ledger - {description}",
                    "source_name": source_name,
                    "destination_name": destination_name,
                    "category_name": record["category"] or "Uncategorized",
                    "notes": notes,
                    "external_id": f"zai-ledger-{record['trans_id']}",
                    "tags": ["zai-ledger", "zaitullah-jan", "single-control-ledger"],
                }
            ],
        }

    def execute(self, target_path, is_live, log, prog):
        self.cancel_requested = False
        self.reset_run_state()
        del target_path

        url, token = self.resolve_credentials()
        if not url or not token:
            message = "Provide Firefly URL and token or set FIREFLY_URL/FIREFLY_TOKEN."
            log(f"ERROR: {message}")
            self.set_run_status("failed", message)
            prog(100)
            return

        if is_live:
            import requests

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.api+json",
            "Content-Type": "application/json",
        }

        created = 0
        failed = 0
        total = len(RAW_TRANSACTIONS)

        log(f"Zai ledger importer {'LIVE' if is_live else 'SCAN'}")
        log(f"Target API: {url}")
        log(f"Ledger account: {LEDGER_ACCOUNT}")
        log("-" * 56)

        for index, record in enumerate(RAW_TRANSACTIONS, start=1):
            if self.cancel_requested:
                log("Canceled by user.")
                break

            payload = self.build_payload(record)
            if payload is None:
                log(f"SKIP ZERO: {record['trans_id']}")
                prog(index / total * 100)
                continue

            tx = payload["transactions"][0]
            if not is_live:
                log(f"Would create: {record['trans_id']}  {tx['type'].upper()}  amount={tx['amount']}  date={tx['date']}  desc={tx['description']}")
            else:
                response = requests.post(f"{url}/api/v1/transactions", headers=headers, json=payload, timeout=30)
                if response.status_code not in (200, 201):
                    failed += 1
                    log(f"FAILED {response.status_code}: {record['trans_id']}")
                    log(response.text)
                else:
                    created += 1
                    log(f"CREATED: {record['trans_id']}  {tx['type'].upper()}  amount={tx['amount']}  date={tx['date']}")

            prog(index / total * 100)

        if not self.cancel_requested:
            if is_live:
                log(f"Done. Created: {created}. Failed/skipped: {failed}.")
                if failed:
                    self.set_run_status("warning", f"{failed} ledger transaction(s) failed to import")
            else:
                log(f"Preview complete. {total} bundled records reviewed.")
