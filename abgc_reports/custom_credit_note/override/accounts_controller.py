import frappe
from frappe import _
from  erpnext.controllers.accounts_controller import (
    AccountsController, 
    set_balance_in_account_currency,
    update_gl_dict_with_regional_fields,
)
from frappe.utils import (
	flt,
	formatdate,
)
from erpnext.accounts.utils import (
	get_account_currency,
	get_fiscal_years,
)
from erpnext.utilities.regional import temporary_flag
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.general_ledger import get_round_off_account_and_cost_center


# class OverrideAccountsController(AccountsController):
def get_gl_dict(self, args, account_currency=None, item=None):
    print("LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL")
    """this method populates the common properties of a gl entry record"""
    
    posting_date = args.get("posting_date") or self.get("posting_date")
    fiscal_years = get_fiscal_years(posting_date, company=self.company)
    if len(fiscal_years) > 1:
        frappe.throw(
            _("Multiple fiscal years exist for the date {0}. Please set company in Fiscal Year").format(
                formatdate(posting_date)
            )
        )
    else:
        fiscal_year = fiscal_years[0][0]
        
    gl_dict = frappe._dict(
        {
            "company": self.company,
            "posting_date": posting_date,
            "fiscal_year": fiscal_year,
            "voucher_type": self.doctype,
            "voucher_no": self.name,
            "remarks": self.get("remarks") or self.get("remark"),
            "debit": 0,
            "credit": 0,
            "debit_in_account_currency": 0,
            "credit_in_account_currency": 0,
            "is_opening": self.get("is_opening") or "No",
            "party_type": None,
            "party": None,
            "project": self.get("project"),
            "post_net_value": args.get("post_net_value"),
        }
    )
    
    with temporary_flag("company", self.company):
        update_gl_dict_with_regional_fields(self, gl_dict)
        
    accounting_dimensions = get_accounting_dimensions()
    dimension_dict = frappe._dict()
    
    for dimension in accounting_dimensions:
        dimension_dict[dimension] = self.get(dimension)
        if item and item.get(dimension):
            dimension_dict[dimension] = item.get(dimension)
            
    gl_dict.update(dimension_dict)
    gl_dict.update(args)
    
    if not account_currency:
        account_currency = get_account_currency(gl_dict.account)
        
    if gl_dict.account and self.doctype not in [
        "Journal Entry",
        "Period Closing Voucher",
        "Payment Entry",
        "Purchase Receipt",
        "Purchase Invoice",
        "Custom Credit Note",
        "Stock Entry",
    ]:
        self.validate_account_currency(gl_dict.account, account_currency)
    
    if gl_dict.account and self.doctype not in [
        "Journal Entry",
        "Period Closing Voucher",
        "Payment Entry",
    ]:
        set_balance_in_account_currency(
            gl_dict, account_currency, self.get("conversion_rate"), self.company_currency
        )
    
    return gl_dict


def make_precision_loss_gl_entry(self, gl_entries):
    print("OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOoo")
    round_off_account, round_off_cost_center = get_round_off_account_and_cost_center(
        self.company, "Purchase Invoice", self.name, self.use_company_roundoff_cost_center
    )
    
    precision_loss = self.get("base_net_total") - flt(
        self.get("net_total") * self.conversion_rate, self.precision("net_total")
    )
    
    credit_or_debit = "credit" if self.doctype == "Purchase Invoice" or self.doctype == "Custom Credit Note" else "debit"
    against = self.supplier if self.doctype == "Purchase Invoice" or self.doctype == "Custom Credit Note" else self.customer
    
    if precision_loss:
        gl_entries.append(
            self.get_gl_dict(
                {
                    "account": round_off_account,
                    "against": against,
                    credit_or_debit: precision_loss,
                    "cost_center": round_off_cost_center
                    if self.use_company_roundoff_cost_center
                    else self.cost_center or round_off_cost_center,
                    "remarks": _("Net total calculation precision loss"),
                }
            )
        )