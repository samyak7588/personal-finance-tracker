"""
Personal Finance Tracker - CSE Mini Project
A desktop GUI app to track income/expenses, with JSON persistence,
category summaries, and a text-based chart.

Run:  python finance_tracker.py
"""

import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "transactions.json")

CATEGORIES_INCOME = ["Salary", "Freelance", "Gift", "Interest", "Other Income"]
CATEGORIES_EXPENSE = ["Food", "Travel", "Rent", "Shopping", "Bills", "Entertainment", "Health", "Other"]


# ---------------- Data Layer ----------------

def load_transactions():
    """Load transactions from JSON file. Returns [] if file missing/corrupt."""
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_transactions(transactions):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(transactions, f, indent=2)


# ---------------- Business Logic ----------------

def add_transaction(txns, t_type, category, amount, note):
    """Append a transaction dict. Raises ValueError on bad input."""
    if t_type not in ("Income", "Expense"):
        raise ValueError("Type must be Income or Expense")
    amount = float(amount)
    if amount <= 0:
        raise ValueError("Amount must be greater than zero")
    txns.append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "type": t_type,
        "category": category,
        "amount": round(amount, 2),
        "note": note.strip(),
    })


def totals(txns):
    income = sum(t["amount"] for t in txns if t["type"] == "Income")
    expense = sum(t["amount"] for t in txns if t["type"] == "Expense")
    return income, expense, income - expense


def category_breakdown(txns, t_type):
    """Return {category: total} sorted by amount desc for a given type."""
    breakdown = {}
    for t in txns:
        if t["type"] == t_type:
            breakdown[t["category"]] = breakdown.get(t["category"], 0) + t["amount"]
    return dict(sorted(breakdown.items(), key=lambda kv: kv[1], reverse=True))


def bar_chart(breakdown, width=40):
    """Simple ASCII bar chart of a breakdown dict."""
    if not breakdown:
        return "(no data)"
    biggest = max(breakdown.values())
    lines = []
    for cat, amt in breakdown.items():
        bars = int(round(amt / biggest * width))
        lines.append(f"{cat:<15} | {'#' * bars} {amt:.2f}")
    return "\n".join(lines)


# ---------------- GUI ----------------

class FinanceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Personal Finance Tracker")
        self.root.geometry("820x560")
        self.txns = load_transactions()

        # --- Summary bar ---
        summary = ttk.Frame(root, padding=10)
        summary.pack(fill="x")
        self.lbl_income = tk.Label(summary, text="Income: 0.00", fg="green", font=("Segoe UI", 12, "bold"))
        self.lbl_income.pack(side="left", padx=15)
        self.lbl_expense = tk.Label(summary, text="Expense: 0.00", fg="red", font=("Segoe UI", 12, "bold"))
        self.lbl_expense.pack(side="left", padx=15)
        self.lbl_balance = tk.Label(summary, text="Balance: 0.00", font=("Segoe UI", 12, "bold"))
        self.lbl_balance.pack(side="right", padx=15)

        # --- Input form ---
        form = ttk.LabelFrame(root, text="Add Transaction", padding=10)
        form.pack(fill="x", padx=10)

        ttk.Label(form, text="Type:").grid(row=0, column=0)
        self.type_var = tk.StringVar(value="Expense")
        type_box = ttk.Combobox(form, textvariable=self.type_var, values=["Expense", "Income"],
                                state="readonly", width=12)
        type_box.grid(row=0, column=1, padx=5)
        type_box.bind("<<ComboboxSelected>>", lambda e: self.update_categories())

        ttk.Label(form, text="Category:").grid(row=0, column=2)
        self.cat_var = tk.StringVar()
        self.cat_box = ttk.Combobox(form, textvariable=self.cat_var, state="readonly", width=16)
        self.cat_box.grid(row=0, column=3, padx=5)

        ttk.Label(form, text="Amount:").grid(row=0, column=4)
        self.amt_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.amt_var, width=10).grid(row=0, column=5, padx=5)

        ttk.Label(form, text="Note:").grid(row=1, column=0, pady=6)
        self.note_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.note_var, width=42).grid(row=1, column=1, columnspan=3, sticky="w", padx=5)

        ttk.Button(form, text="Add", command=self.on_add).grid(row=1, column=4, columnspan=2, pady=6)
        self.update_categories()

        # --- Table ---
        table_frame = ttk.Frame(root, padding=(10, 5))
        table_frame.pack(fill="both", expand=True)
        cols = ("date", "type", "category", "amount", "note")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=12)
        widths = (140, 70, 110, 80, 300)
        for c, w in zip(cols, widths):
            self.tree.heading(c, text=c.title())
            self.tree.column(c, width=w)
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.tree.tag_configure("Income", foreground="green")
        self.tree.tag_configure("Expense", foreground="black")

        # --- Bottom buttons + report ---
        bottom = ttk.Frame(root, padding=10)
        bottom.pack(fill="x")
        ttk.Button(bottom, text="Delete Selected", command=self.on_delete).pack(side="left", padx=5)
        ttk.Button(bottom, text="Show Category Report", command=self.on_report).pack(side="left", padx=5)
        ttk.Button(bottom, text="Export Report (.txt)", command=self.on_export).pack(side="left", padx=5)

        self.refresh_table()

    def update_categories(self):
        cats = CATEGORIES_EXPENSE if self.type_var.get() == "Expense" else CATEGORIES_INCOME
        self.cat_box["values"] = cats
        self.cat_var.set(cats[0])

    def refresh_table(self):
        self.tree.delete(*self.tree.get_children())
        for i, t in enumerate(self.txns):
            self.tree.insert("", "end", iid=str(i), values=(
                t["date"], t["type"], t["category"], f"{t['amount']:.2f}", t["note"]),
                tags=(t["type"],))
        income, expense, balance = totals(self.txns)
        self.lbl_income.config(text=f"Income: {income:,.2f}")
        self.lbl_expense.config(text=f"Expense: {expense:,.2f}")
        self.lbl_balance.config(
            text=f"Balance: {balance:,.2f}",
            fg="green" if balance >= 0 else "red")

    def on_add(self):
        try:
            add_transaction(self.txns, self.type_var.get(), self.cat_var.get(),
                            self.amt_var.get(), self.note_var.get())
        except ValueError as e:
            messagebox.showerror("Invalid input", str(e))
            return
        save_transactions(self.txns)
        self.amt_var.set("")
        self.note_var.set("")
        self.refresh_table()

    def on_delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Delete", "Select a row first.")
            return
        for iid in sorted(sel, key=int, reverse=True):
            del self.txns[int(iid)]
        save_transactions(self.txns)
        self.refresh_table()

    def on_report(self):
        rep = (
            "===== CATEGORY REPORT =====\n\nINCOME:\n"
            + bar_chart(category_breakdown(self.txns, "Income"))
            + "\n\nEXPENSES:\n"
            + bar_chart(category_breakdown(self.txns, "Expense")))
        win = tk.Toplevel(self.root)
        win.title("Category Report")
        txt = tk.Text(win, width=75, height=22, font=("Consolas", 10))
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", rep)
        txt.config(state="disabled")

    def on_export(self):
        path = os.path.join(os.path.dirname(DATA_FILE), "report.txt")
        income, expense, balance = totals(self.txns)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"PERSONAL FINANCE REPORT  ({datetime.now():%Y-%m-%d %H:%M})\n")
            f.write("=" * 50 + "\n\n")
            for t in self.txns:
                f.write(f"{t['date']}  {t['type']:<7} {t['category']:<14} "
                        f"{t['amount']:>10.2f}  {t['note']}\n")
            f.write("\n" + "=" * 50 + "\n")
            f.write(f"Total Income : {income:>10.2f}\n")
            f.write(f"Total Expense: {expense:>10.2f}\n")
            f.write(f"Balance      : {balance:>10.2f}\n\n")
            f.write("EXPENSE BREAKDOWN\n" + bar_chart(category_breakdown(self.txns, "Expense")))
        messagebox.showinfo("Exported", f"Report saved to:\n{path}")


if __name__ == "__main__":
    root = tk.Tk()
    FinanceApp(root)
    root.mainloop()
