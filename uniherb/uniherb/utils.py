import json
from datetime import date

import dateutil.utils

import frappe
from erpnext.accounts.party import get_party_details
from frappe import _, qb
from frappe.desk.utils import slug
from frappe.utils import get_url, quoted


@frappe.whitelist()
def fetch_recent_soled_items(**args):
    item_code = args.get('item_code')
    data = {}
    data['sales_history'] = frappe.db.sql(
        """
        select 
            `tabSales Invoice Item`.name, `tabSales Invoice Item`.parent,
            `tabSales Invoice`.posting_date,`tabSales Invoice`.customer_name,
            `tabSales Invoice Item`.item_code,`tabSales Invoice Item`.`item_name`,
            `tabSales Invoice Item`.rate
        from `tabSales Invoice`, `tabSales Invoice Item`
        where `tabSales Invoice`.name = `tabSales Invoice Item`.parent
            and `tabSales Invoice`.docstatus = 1 and `tabSales Invoice Item`.item_code = %s  order by `tabSales Invoice Item`.parent 
        """,(item_code, ),
        as_dict=1
    )[:5]

    data['purchase_history'] = frappe.db.sql(
        """
        select 
            `tabPurchase Invoice Item`.name, `tabPurchase Invoice Item`.parent,
            `tabPurchase Invoice`.posting_date,`tabPurchase Invoice`.supplier_name,
            `tabPurchase Invoice Item`.item_code,`tabPurchase Invoice Item`.`item_name`,
            `tabPurchase Invoice Item`.rate
        from `tabPurchase Invoice`, `tabPurchase Invoice Item`
        where `tabPurchase Invoice`.name = `tabPurchase Invoice Item`.parent
            and `tabPurchase Invoice`.docstatus = 1 and `tabPurchase Invoice Item`.item_code = %s  order by `tabPurchase Invoice Item`.parent 
        """, (item_code,),
        as_dict=1
    )[:5]
    return data

@frappe.whitelist()
def fetch_recent_purchased_items(**args):
    item_code = args.get('item_code')
    data = frappe.db.sql(
        """
        select 
            `tabPurchase Invoice Item`.name, `tabPurchase Invoice Item`.parent,
            `tabPurchase Invoice`.posting_date,`tabPurchase Invoice`.supplier_name,
            `tabPurchase Invoice Item`.item_code,`tabPurchase Invoice Item`.`item_name`,
            `tabPurchase Invoice Item`.rate
        from `tabPurchase Invoice`, `tabPurchase Invoice Item`
        where `tabPurchase Invoice`.name = `tabPurchase Invoice Item`.parent
            and `tabPurchase Invoice`.docstatus = 1 and `tabPurchase Invoice Item`.item_code = %s  order by `tabPurchase Invoice Item`.parent 
        """, (item_code,),
        as_dict=1
    )[:5]
    return data

@frappe.whitelist()
def fetch_child_records(**args):
    child_records = frappe.get_all("Receipt Form Item", filters={"payment_form_id": args.get("master_name")},
                                   fields=["name",
                                           "mode_of_payment",
                                           "in_date",
                                           "bank_name",
                                           "account_title",
                                           "cheque_no",
                                           "bank_date",
                                           "amount",
                                           "in_party",
                                           "out_party",
                                           "out_date",
                                           "slip_no",
                                           "name_id"
                                           ]
                                   )
    return child_records


@frappe.whitelist()
def get_receipts(**args):
    rfi = frappe.qb.DocType("Receipt Form Item")
    query = (
        frappe.qb.from_(rfi)
        .select(rfi.name,
                rfi.mode_of_payment,
                rfi.in_date,
                rfi.bank_name,
                rfi.account_title,
                rfi.cheque_no,
                rfi.bank_date,
                rfi.amount,
                rfi.out_party,
                rfi.in_party,
                rfi.out_date,
                rfi.slip_no,
                rfi.name_id
                )
        .where(
            (rfi.status == 'In')
            & (rfi.docstatus == 1)
            # & (je.voucher_type == "Exchange Rate Revaluation")
        )
    )

    if args.get("from_date", None) and args.get("to_date", None):
        query = query.where(
            rfi.in_date.between(args.get("from_date"), args.get("to_date"))
        )
    if args.get("bank_name", None):
        query = query.where(
            rfi.bank_name.like(f"%{args.get('bank_name')}%")
        )
    if args.get("account_title", None):
        query = query.where(
            rfi.account_title.like(f"%{args.get('account_title')}%")
        )
    if args.get("mode_of_payment", None):
        query = query.where(
            rfi.mode_of_payment == args.get('mode_of_payment')
        )
    if args.get("cheque_no", None):
        query = query.where(
            rfi.cheque_no.like(f"%{args.get('cheque_no')}%")
        )
    if args.get("bank_date", None):
        query = query.where(
            rfi.bank_date == args.get('bank_date')
        )
    if args.get("slip_no", None):
        query = query.where(
            rfi.slip_no == args.get('slip_no')
        )
    return query.run(as_dict=True)


@frappe.whitelist()
def cancel_payment_form(**args):
    receipt_form_item = json.loads(args.get('receipt_form_item'))
    for item in receipt_form_item:
        rfi = frappe.get_doc("Receipt Form Item", item['id'])
        rfi.reload()
        rfi.payment_form_id = None
        rfi.status = 'In'
        rfi.out_party = None
        rfi.out_date = None
        rfi.save()
    frappe.db.delete("Payment Form", args.get('parent'))
    return "Cancelled"


def get_cost_center_and_income_account(company):
    income_account, cost_center = frappe.get_cached_value(
        "Company", company, ["default_income_account", "cost_center"]
    )

    if not income_account:
        frappe.throw(
            _("Please set 'Income account' in Company {0}").format(company)
        )
    if not cost_center:
        frappe.throw(_("Please set 'Cost Center' in Company {0}").format(company))
    data = {'income_account': income_account, 'cost_center': cost_center}
    return data


def get_url_to_form(doctype: str, name: str) -> str:
    return get_url(uri=f"/app/{quoted(slug(doctype))}/{quoted(name)}")


def get_link_to_form(doctype: str, name: str, label: str | None = None) -> str:
    if not label:
        label = name

    return f"""<a href="{get_url_to_form(doctype, name)}">{label}</a>"""


def get_bank_cash_account(mode_of_payment, company):
    account = frappe.db.get_value(
        "Mode of Payment Account", {"parent": mode_of_payment, "company": company}, "default_account"
    )
    if not account:
        frappe.throw(
            _("Please set default Cash or Bank account in Mode of Payment {0}").format(
                get_link_to_form("Mode of Payment", mode_of_payment)
            ),
            title=_("Missing Account"),
        )
    return {"account": account}


def get_party_gle_currency(party_type, party, company):
    def generator():
        existing_gle_currency = frappe.db.sql(
            """select account_currency from `tabGL Entry`
            where docstatus=1 and company=%(company)s and party_type=%(party_type)s and party=%(party)s
            limit 1""",
            {"company": company, "party_type": party_type, "party": party},
        )

        return existing_gle_currency[0][0] if existing_gle_currency else None

    return frappe.local_cache(
        "party_gle_currency", (party_type, party, company), generator, regenerate_if_none=True
    )


def get_party_gle_account(party_type, party, company):
    def generator():
        existing_gle_account = frappe.db.sql(
            """select account from `tabGL Entry`
            where docstatus=1 and company=%(company)s and party_type=%(party_type)s and party=%(party)s
            limit 1""",
            {"company": company, "party_type": party_type, "party": party},
        )

        return existing_gle_account[0][0] if existing_gle_account else None

    return frappe.local_cache(
        "party_gle_account", (party_type, party, company), generator, regenerate_if_none=True
    )


def get_party_account(party_type, party=None, company=None):
    """Returns the account for the given `party`.
    Will first search in party (Customer / Supplier) record, if not found,
    will search in group (Customer Group / Supplier Group),
    finally will return default."""
    if not company:
        frappe.throw(_("Please select a Company"))

    if not party and party_type in ["Customer", "Supplier"]:
        default_account_name = (
            "default_receivable_account" if party_type == "Customer" else "default_payable_account"
        )

        return frappe.get_cached_value("Company", company, default_account_name)

    account = frappe.db.get_value(
        "Party Account", {"parenttype": party_type, "parent": party, "company": company}, "account"
    )

    if not account and party_type in ["Customer", "Supplier"]:
        party_group_doctype = "Customer Group" if party_type == "Customer" else "Supplier Group"
        group = frappe.get_cached_value(party_type, party, frappe.scrub(party_group_doctype))
        account = frappe.db.get_value(
            "Party Account",
            {"parenttype": party_group_doctype, "parent": group, "company": company},
            "account",
        )

    if not account and party_type in ["Customer", "Supplier"]:
        default_account_name = (
            "default_receivable_account" if party_type == "Customer" else "default_payable_account"
        )
        account = frappe.get_cached_value("Company", company, default_account_name)

    existing_gle_currency = get_party_gle_currency(party_type, party, company)
    if existing_gle_currency:
        if account:
            account_currency = frappe.db.get_value("Account", account, "account_currency", cache=True)
        if (account and account_currency != existing_gle_currency) or not account:
            account = get_party_gle_account(party_type, party, company)

    return account


@frappe.whitelist()
def payment_entry_from_receipt_form(source_name):
    source_name = frappe.get_doc("Receipt Form", source_name)
    if len(source_name.receipt_form_item) > 0:
        if not source_name.payment_entry_done:
            currency = frappe.defaults.get_defaults().currency
            company = frappe.defaults.get_defaults().company
            posting_date = source_name.posting_date
            try:
                cost_center_and_income_ac_dict = get_cost_center_and_income_account(company)
                cost_center = cost_center_and_income_ac_dict['cost_center']
            except:
                frappe.throw("Error occured finding cost center")
            payment_type = 'Receive'
            party_type = 'Customer'
            party = source_name.party
            party_name = source_name.party_name
            try:
                paid_from = get_party_account(party_type, party=party, company=company)
            except:
                frappe.throw("Error occured finding paid from account ")
            tr_no = source_name.tr_no
            for item in source_name.receipt_form_item:
                try:
                    pe = frappe.new_doc("Payment Entry")
                    pe.posting_date = posting_date
                    pe.payment_type = payment_type
                    pe.party_type = party_type
                    pe.party = party
                    pe.party_name = party_name
                    pe.paid_to = get_bank_cash_account(item.mode_of_payment, company)['account']
                    pe.paid_from_account_currency = currency
                    pe.paid_to_account_currency = currency
                    pe.paid_amount = item.amount
                    pe.company = company
                    pe.cost_center = cost_center
                    pe.target_exchange_rate = 1
                    pe.source_exchange_rate = 1
                    pe.base_paid_amount = item.amount
                    pe.base_received_amount = item.amount
                    pe.received_amount = item.amount
                    pe.custom_remarks = 1
                    pe.remarks = f"Amount {currency} {item.amount} received from {party_name} Tr # {tr_no}"
                    pe.tr_no = tr_no
                    pe.mode_of_payment = item.mode_of_payment
                    pe.paid_from = paid_from
                    if item.mode_of_payment == 'Online Deposit':
                        pe.slip_no = item.cheque_no
                    if item.mode_of_payment == 'Cheque':
                        pe.reference_no = item.cheque_no
                        pe.reference_date = item.bank_date
                    pe.submit()
                    # return si
                except Exception as error:
                    frappe.throw("Payment Entry Not Created")

            source_name.payment_entry_done = 1
            source_name.save()
        else:
            frappe.throw("Payment Entry already created")
    else:
        frappe.throw("No detail record found")


@frappe.whitelist()
def payment_entry_from_payment_form(**args):
    source_name = frappe.get_doc("Payment Form", args.get('source_name'))
    receipt_form_item = frappe.get_all('Receipt Form Item', filters={'payment_form_id': args.get('source_name')},
                                       fields=['in_date', 'in_party', 'mode_of_payment', 'bank_name', 'account_title',
                                               'cheque_no', 'bank_date', 'amount', 'out_party', 'out_date',
                                               'payment_form_id'
                                           , 'status', 'id','slip_no'])
    if len(receipt_form_item) > 0:
        if not source_name.payment_entry_done:
            currency = frappe.defaults.get_defaults().currency
            company = frappe.defaults.get_defaults().company
            posting_date = source_name.posting_date
            try:
                cost_center_and_income_ac_dict = get_cost_center_and_income_account(company)
                cost_center = cost_center_and_income_ac_dict['cost_center']
            except:
                frappe.throw("Error occured finding cost center")
            payment_type = 'Pay'
            party_type = 'Supplier'
            party = source_name.party
            party_name = source_name.party_name
            try:
                paid_to = get_party_account(party_type, party=party, company=company)
            except:
                frappe.throw("Error occured finding paid from account ")
            tr_no = source_name.tr_no
            for item in receipt_form_item:
                try:
                    pe = frappe.new_doc("Payment Entry")
                    pe.posting_date = posting_date
                    pe.payment_type = payment_type
                    pe.party_type = party_type
                    pe.party = party
                    pe.party_name = party_name
                    pe.paid_to = paid_to
                    pe.paid_from_account_currency = currency
                    pe.paid_to_account_currency = currency
                    pe.paid_amount = item.amount
                    pe.company = company
                    pe.cost_center = cost_center
                    pe.target_exchange_rate = 1
                    pe.source_exchange_rate = 1
                    pe.base_paid_amount = item.amount
                    pe.base_received_amount = item.amount
                    pe.received_amount = item.amount
                    pe.custom_remarks = 1
                    pe.remarks = f"Amount {currency} {item.amount} paid to {party_name} Tr # {tr_no}"
                    pe.tr_no = tr_no
                    pe.mode_of_payment = item.mode_of_payment
                    pe.paid_from = get_bank_cash_account(item.mode_of_payment, company)['account']
                    if item.mode_of_payment == 'Online Deposit':
                        pe.slip_no = item.cheque_no
                    if item.mode_of_payment == 'Cheque':
                        pe.reference_no = item.cheque_no
                        pe.reference_date = item.posting_date
                    pe.submit()
                    # return si
                except Exception as error:
                    frappe.throw("Payment Entry Not Created")
            frappe.db.set_value('Payment Form', args.get('source_name'), 'payment_entry_done',1)
        else:
            frappe.throw("Payment Entry already created")
    else:
        frappe.throw("No detail record found")

@frappe.whitelist()
def fetch_purchased_items_info_by_batch_no(**args):
    item_code = args.get('item_code')
    batch_no = args.get('batch_no')
    data = frappe.db.sql(
        """
        select 
            `tabPurchase Invoice Item`.kg_per_ctn, `tabPurchase Invoice Item`.lbs_per_ctn
        from `tabBatch`, `tabPurchase Invoice Item`
        where `tabBatch`.item = `tabPurchase Invoice Item`.item_code
            and `tabBatch`.batch_id =  `tabPurchase Invoice Item`.batch_no and `tabBatch`.item = %s
             and `tabBatch`.batch_id = %s  order by `tabPurchase Invoice Item`.parent 
        """, (item_code,batch_no,),
        as_dict=1
    )
    return data