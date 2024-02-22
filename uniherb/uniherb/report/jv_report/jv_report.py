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
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "GL Entry",
            "width": 160
        },

        {
            "label": "<b>CREDITOR PARTY</b>",
            "fieldname": "creditor_party",
            "fieldtype": "Data",
            "width": 180
        },
        {
            "label": "<b>DEBITOR PARTY</b>",
            "fieldname": "debitor_party",
            "fieldtype": "Data",
            "width": 180

        },

        {
            "label": "<b>AMOUNT</b>",
            "fieldname": "amount",
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "label": "<b>REMARKS</b>",
            "fieldname": "remarks",
            "fieldtype": "Data",
            "width": 180
        }

    ]
    return columns


def get_conditions(filters):
    conditions = []
    if filters.get("from_date"):
        conditions.append(f"gle.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append(f"gle.posting_date <= %(to_date)s")
    return " AND ".join(conditions)


def get_data(filters):
    data = []
    conditions = get_conditions(filters)

    # Generating SQL subqueries to filter payable and receivable accounts
    payable_subquery = """
            SELECT name FROM `tabAccount` WHERE account_type = 'Payable'
        """
    receivable_subquery = """
            SELECT name FROM `tabAccount` WHERE account_type = 'Receivable'
        """

    gle_query = f"""
            SELECT 
                gle.posting_date,
                gle.name,
                CASE WHEN gle.account IN ({payable_subquery}) THEN gle.party ELSE NULL END AS creditor_party,
                CASE WHEN gle.account IN ({receivable_subquery}) THEN gle.party ELSE NULL END AS debitor_party,
                CASE 
                    WHEN gle.account IN ({payable_subquery}) AND gle.debit > 0 THEN gle.debit 
                    WHEN gle.account IN ({receivable_subquery}) AND gle.credit > 0 THEN gle.credit 
                    ELSE NULL 
                END AS amount,
                gle.remarks
            FROM `tabGL Entry` AS gle
            WHERE 
                {conditions}
                AND gle.is_cancelled = 0
                AND gle.voucher_type = 'Journal Entry'
                AND (gle.account IN ({payable_subquery}) OR gle.account IN ({receivable_subquery}))
                AND ((gle.account IN ({payable_subquery}) AND gle.debit > 0) OR (gle.account IN ({receivable_subquery}) AND gle.credit > 0))
        """

    gle_query_result = frappe.db.sql(gle_query, filters, as_dict=1)

    data.extend(gle_query_result)
    return data



