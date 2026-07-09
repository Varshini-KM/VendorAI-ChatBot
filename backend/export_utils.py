"""
CSV / PDF export for reports. Uses pandas for CSV and fpdf2 (pure-python,
no system dependencies) for a clean one-page PDF summary.
"""
import io
from datetime import date
from fpdf import FPDF
import pandas as pd
from sqlalchemy.orm import Session

from backend import analytics


def export_report_csv(db: Session, vendor_id: int, period: str = "month") -> bytes:
    start, end = analytics._period_bounds(period)
    sales_df = analytics._sales_df(db, vendor_id, start, end)
    exp_df = analytics._expenses_df(db, vendor_id, start, end)

    buf = io.StringIO()
    buf.write(f"VendorAI Report ({period}) {start} to {end}\n\n")
    buf.write("SALES\n")
    sales_df.to_csv(buf, index=False)
    buf.write("\nEXPENSES\n")
    exp_df.to_csv(buf, index=False)

    return buf.getvalue().encode("utf-8")


class ReportPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "VendorAI Business Report", ln=True, align="C")
        self.set_font("Helvetica", "", 10)
        self.cell(0, 8, f"Generated on {date.today().isoformat()}", ln=True, align="C")
        self.ln(4)


def export_report_pdf(db: Session, vendor_id: int, period: str = "month") -> bytes:
    report = analytics.compute_report(db, vendor_id, period)
    inv = analytics.compute_inventory_status(db, vendor_id)

    pdf = ReportPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"Period: {report['period']} ({report['start_date']} to {report['end_date']})", ln=True)
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Total Sales: Rs. {report.get('total_sales', 0):.2f}", ln=True)
    pdf.cell(0, 8, f"Total Expenses: Rs. {report.get('total_expenses', 0):.2f}", ln=True)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, f"Net Profit: Rs. {report.get('profit', 0):.2f}", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Top Products", ln=True)
    pdf.set_font("Helvetica", "", 10)
    if report["top_products"]:
        for p in report["top_products"][:10]:
            pdf.cell(0, 7, f"  {p['product']}: Rs. {p['total_amount']:.2f}", ln=True)
    else:
        pdf.cell(0, 7, "  No sales in this period.", ln=True)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Expense Breakdown", ln=True)
    pdf.set_font("Helvetica", "", 10)
    if report["expense_breakdown"]:
        for e in report["expense_breakdown"]:
            pdf.cell(0, 7, f"  {e['category']}: Rs. {e['amount']:.2f}", ln=True)
    else:
        pdf.cell(0, 7, "  No expenses in this period.", ln=True)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Current Inventory", ln=True)
    pdf.set_font("Helvetica", "", 10)
    if inv["items"]:
        for i in inv["items"]:
            flag = "  (LOW STOCK)" if i["quantity"] <= i["low_stock_threshold"] else ""
            pdf.cell(0, 7, f"  {i['product']}: {i['quantity']} {i['unit']}{flag}", ln=True)
    else:
        pdf.cell(0, 7, "  No inventory items recorded.", ln=True)

    return bytes(pdf.output())
