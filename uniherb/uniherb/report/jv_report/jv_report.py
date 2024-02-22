# my_custom_app.my_custom_app.report.daily_activity_report.daily_activity_report.py
from decimal import Decimal

import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    columns = [
        {
            "label": "<b>DATE</b>",
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 150
        },
        {
            "label": "<b>JV NO</b>",
            "fieldname": "voucher_no",
            "fieldtype": "Link",
            "options": "Journal Entry",
            "width": 160
        },
        {
          "label": "<b>ACCOUNT</b>",
          "fieldname": "party_type",
          "fieldtype": "Data",
          "width": 180
        },

        {
            "label": "<b>PARTY</b>",
            "fieldname": "party",
            "fieldtype": "Data",
            "width": 180
        },
        {
            "label": "<b>DEBIT</b>",
            "fieldname": "debit",
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "label": "<b>CREDIT</b>",
            "fieldname": "credit",
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "label": "<b>REMARKS</b>",
            "fieldname": "user_remark",
            "fieldtype": "Data",
            "width": 180
        }

    ]
    return columns


def get_conditions(filters):
    conditions = []
    if filters.get("from_date"):
        conditions.append(f"je.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append(f"je.posting_date <= %(to_date)s")
    return " AND ".join(conditions)


def get_data(filters):
    data = []
    conditions = get_conditions(filters)
    gle_query = f"""
            SELECT 
                je.posting_date,
                je.name AS voucher_no,
                jea.party_type,
                jea.party,
                jea.debit,
                jea.credit,
                jea.user_remark
            FROM 
                `tabJournal Entry` AS je
            JOIN 
                `tabJournal Entry Account` AS jea ON je.name = jea.parent
            WHERE 
                jea.account IN ('Debtors - UH', 'Creditors - UH')
                AND jea.party_type IN ('Customer', 'Supplier')
                AND je.docstatus = 1
                AND je.name IN (
                    SELECT parent 
                    FROM `tabJournal Entry Account` 
                    WHERE account IN ('Debtors - UH', 'Creditors - UH')
                    GROUP BY parent 
                    HAVING COUNT(DISTINCT account) = 2
                )
                AND {conditions}
            ORDER BY 
                je.name
        """
    # Execute your SQL query here using gle_query


    gle_query_result = frappe.db.sql(gle_query, filters, as_dict=1)

    data.extend(gle_query_result)
    return data



