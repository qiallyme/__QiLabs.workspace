from __future__ import annotations

import os
import tkinter as tk
from datetime import date
from tkinter import ttk

from core.base_tool import BaseTool


BILLS = [
    {"name": "Mom - Affirm", "amount": "69.73", "day": 29, "group": "Mom Monthly Bills", "category": "Debt / Installments", "notes": "Imported from Mom Monthly Budget. Original listed date looked wrong; treated as monthly due on the 29th."},
    {"name": "Mom - Rent", "amount": "213.00", "day": 3, "group": "Mom Monthly Bills", "category": "Housing", "notes": "Imported from Mom Monthly Budget."},
    {"name": "Mom - Capital One", "amount": "25.00", "day": 3, "group": "Mom Monthly Bills", "category": "Credit Card", "notes": "Imported from Mom Monthly Budget."},
    {"name": "Mom - Credit One", "amount": "30.00", "day": 5, "group": "Mom Monthly Bills", "category": "Credit Card", "notes": "Imported from Mom Monthly Budget."},
    {"name": "Mom - Hulu", "amount": "11.99", "day": 5, "group": "Mom Monthly Bills", "category": "Subscriptions", "notes": "Imported from Mom Monthly Budget."},
    {"name": "Mom - Google Storage", "amount": "1.99", "day": 8, "group": "Mom Monthly Bills", "category": "Subscriptions", "notes": "Imported from Mom Monthly Budget."},
    {"name": "Mom - Direct Auto", "amount": "83.97", "day": 13, "group": "Mom Monthly Bills", "category": "Insurance", "notes": "Imported from Mom Monthly Budget."},
    {"name": "Mom - AT&T", "amount": "30.00", "day": 13, "group": "Mom Monthly Bills", "category": "Phone", "notes": "Imported from Mom Monthly Budget."},
    {"name": "Mom - Discovery+", "amount": "9.99", "day": 14, "group": "Mom Monthly Bills", "category": "Subscriptions", "notes": "Imported from Mom Monthly Budget."},
    {"name": "Mom - Astound", "amount": "30.00", "day": 20, "group": "Mom Monthly Bills", "category": "Internet & Phone", "notes": "Imported from Mom Monthly Budget."},
    {"name": "Mom - Amazon Card", "amount": "29.00", "day": 21, "group": "Mom Monthly Bills", "category": "Credit Card", "notes": "Imported from Mom Monthly Budget."},
    {"name": "Mom - Credit One 2", "amount": "60.00", "day": 21, "group": "Mom Monthly Bills", "category": "Credit Card", "notes": "Imported from Mom Monthly Budget."},
    {"name": "Mom - Amazon Prime", "amount": "6.99", "day": 29, "group": "Mom Monthly Bills", "category": "Subscriptions", "notes": "Imported from Mom Monthly Budget. Original listed date was old; treated as monthly due on the 29th."},
    {"name": "Mom - Parklawn", "amount": "79.00", "day": 29, "group": "Mom Monthly Bills", "category": "Debt / Installments", "notes": "Imported from Mom Monthly Budget. Original listed date was old; treated as monthly due on the 29th."},
    {"name": "Shared Home - Rent", "amount": "700.00", "day": 1, "group": "Shared Home Expenses", "category": "Housing", "notes": "Confirmed shared home expense."},
    {"name": "Shared Home - Electric", "amount": "160.00", "day": 10, "group": "Shared Home Expenses", "category": "Utilities", "notes": "Estimated normal bill. Current bill paid by Medicare and CAPE this time; account has credit balance. Do not treat as currently owed without checking balance."},
    {"name": "Shared Home - Water", "amount": "80.00", "day": 15, "group": "Shared Home Expenses", "category": "Utilities", "notes": "Tracker estimate listed $80 and due date 15th, but account note says due on the 3rd. Verify actual due date in portal before relying on this record."},
    {"name": "Shared Home - Astound Internet & Phones", "amount": "30.00", "day": 20, "group": "Shared Home Expenses", "category": "Internet & Phone", "notes": "Astound internet and phones. Household tracker had old internet estimate of $40; using $30 from Mom Monthly Budget unless verified otherwise."},
    {"name": "Shared Home - Car Insurance", "amount": "50.00", "day": 5, "group": "Shared Home Expenses", "category": "Insurance", "notes": "Estimated shared home tracker amount."},
    {"name": "Shared Home - Supplies", "amount": "20.00", "day": 25, "group": "Shared Home Expenses", "category": "Household", "notes": "Estimated shared home supplies."},
    {"name": "Shared Home - Washer and Dryer", "amount": "132.00", "day": 7, "group": "Shared Home Expenses", "category": "Laundry", "notes": "Confirmed. Actual payment pattern is $33 weekly. Firefly monthly bill record uses $132 monthly approximation; consider separate weekly recurring setup later."},
    {"name": "Shared Home - Groceries", "amount": "128.00", "day": 1, "group": "Shared Home Expenses", "category": "Groceries", "notes": "Estimated grocery budget line. Not a true payable bill, but useful for household budget tracking."},
    {"name": "Cody - ElevenLabs", "amount": "5.00", "day": 27, "group": "Cody Personal Bills", "category": "AI Tools", "notes": "Personal monthly bill tracker."},
    {"name": "Cody - ChatGPT", "amount": "24.00", "day": 25, "group": "Cody Personal Bills", "category": "AI Tools", "notes": "Personal monthly bill tracker."},
    {"name": "Cody - Brigit", "amount": "52.99", "day": 30, "group": "Cody Personal Bills", "category": "Loans", "notes": "Personal monthly bill tracker."},
    {"name": "Cody - Cash App Loans", "amount": "45.00", "day": 20, "group": "Cody Personal Bills", "category": "Loans", "notes": "Personal monthly bill tracker."},
    {"name": "Cody - Afterpay Loans", "amount": "20.00", "day": 5, "group": "Cody Personal Bills", "category": "Loans", "notes": "Personal monthly bill tracker."},
    {"name": "Cody - Tello Phone", "amount": "27.00", "day": 3, "group": "Cody Personal Bills", "category": "Phone", "notes": "Personal monthly bill tracker."},
]


class FireflyBillsImporterTool(BaseTool):
    def __init__(self):
        self.cancel_requested = False
        self.url_var = None
        self.token_var = None
        self.group_filter_var = None

    def get_name(self):
        return "Firefly Bills Importer"

    def build_ui(self, parent):
        ttk.Label(parent, text="Create recurring bill records in Firefly III from the bundled household bill list.", background="#121a2b", foreground="white").pack(anchor="w", pady=(0, 10))

        defaults = {
            "Firefly URL (blank = FIREFLY_URL env var)": tk.StringVar(value=os.environ.get("FIREFLY_URL", "")),
            "Access token (blank = FIREFLY_TOKEN env var)": tk.StringVar(value=""),
            "Optional group filter": tk.StringVar(value=""),
        }
        self.url_var = list(defaults.values())[0]
        self.token_var = list(defaults.values())[1]
        self.group_filter_var = list(defaults.values())[2]

        for label, variable in defaults.items():
            ttk.Label(parent, text=label, background="#121a2b", foreground="white").pack(anchor="w", pady=(0, 4))
            entry = tk.Entry(
                parent,
                textvariable=variable,
                bg="#10192a",
                fg="white",
                insertbackground="white",
                relief="flat",
                show="*" if "token" in label.lower() else "",
            )
            entry.pack(fill="x", ipady=6, pady=(0, 10))

        ttk.Label(parent, text=f"Bundled records: {len(BILLS)}", background="#121a2b", foreground="#8ea2c7").pack(anchor="w")

    def resolve_credentials(self):
        url = (self.url_var.get().strip() or os.environ.get("FIREFLY_URL", "")).rstrip("/")
        token = self.token_var.get().strip() or os.environ.get("FIREFLY_TOKEN", "")
        return url, token

    def next_bill_date(self, day):
        today = date.today()
        day = min(day, 28) if today.month == 2 else day
        candidate = date(today.year, today.month, day)
        if candidate < today:
            if today.month == 12:
                return date(today.year + 1, 1, min(day, 28)).isoformat()
            return date(today.year, today.month + 1, day).isoformat()
        return candidate.isoformat()

    def build_payload(self, record):
        amount = record["amount"]
        return {
            "name": record["name"],
            "amount_min": amount,
            "amount_max": amount,
            "date": self.next_bill_date(record["day"]),
            "repeat_freq": "monthly",
            "active": True,
            "notes": (
                f"{record.get('notes', '')}\n\n"
                f"Group: {record.get('group', '')}\n"
                f"Category: {record.get('category', '')}\n"
                "Imported by QiOne Firefly Bills Importer."
            ),
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

        group_filter = self.group_filter_var.get().strip().lower()
        records = [bill for bill in BILLS if not group_filter or group_filter in bill["group"].lower()]
        total = len(records)

        log(f"Firefly bills importer {'LIVE' if is_live else 'SCAN'}")
        log(f"Target API: {url}")
        log(f"Matched records: {total}")
        log("-" * 56)

        if not total:
            message = "No records matched the current group filter."
            log(message)
            self.set_run_status("warning", message)
            prog(100)
            return

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.api+json",
            "Content-Type": "application/json",
        }

        if is_live:
            import requests

        created = 0
        failed = 0

        for index, record in enumerate(records, start=1):
            if self.cancel_requested:
                log("Canceled by user.")
                break

            payload = self.build_payload(record)
            if not is_live:
                log(f"Would create: {record['name']}  amount={record['amount']}  group={record['group']}  first_date={payload['date']}")
            else:
                response = requests.post(f"{url}/api/v1/bills", headers=headers, json=payload, timeout=30)
                if response.status_code not in (200, 201):
                    failed += 1
                    log(f"FAILED {response.status_code}: {record['name']}")
                    log(response.text)
                else:
                    created += 1
                    log(f"CREATED: {record['name']}  amount={record['amount']}")

            prog(index / total * 100)

        if not self.cancel_requested:
            if is_live:
                log(f"Done. Created: {created}. Failed: {failed}.")
                if failed:
                    self.set_run_status("warning", f"{failed} bill record(s) failed to import")
            else:
                log(f"Preview complete. {total} records matched.")
