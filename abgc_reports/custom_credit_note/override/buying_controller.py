import frappe
from frappe import _
from  erpnext.controllers.buying_controller import (
    BuyingController, 
)
from erpnext.buying.utils import update_last_purchase_rate, validate_for_items
from frappe.utils.data import flt
    
    
def get_asset_items(self):
    if self.doctype not in ["Purchase Order", "Purchase Invoice", "Purchase Receipt", "FA Credit Note"]:
        return []
    
    return [d.item_code for d in self.items if d.is_fixed_asset]
    

def on_submit(self):
    if self.get("is_return"):
        return

    if self.doctype in ["Purchase Receipt", "Purchase Invoice", "FA Credit Note"]:
        if self.doctype == "Purchase Invoice":
            field = "purchase_invoice"
        elif self.doctype == "FA Credit Note":
            field = "custom_fa_credit_note"
        else:
            field ="purchase_receipt"
        print(2222222222222222, field)
        self.process_fixed_asset()
        self.update_fixed_asset(field)
    
    if self.doctype in ["Purchase Order", "Purchase Receipt"] and not frappe.db.get_single_value(
        "Buying Settings", "disable_last_purchase_rate"
    ):
        update_last_purchase_rate(self, is_submit=1)


def process_fixed_asset(self):
    print(8888888888888888888888,self.doctype,self.update_stock)
    if (self.doctype == "Purchase Invoice" or self.doctype == "FA Credit Note") and not self.update_stock:
        print(999999999999999999)
        return

    asset_items = self.get_asset_items()
    if asset_items:
        self.auto_make_assets(asset_items)


def make_asset(self, row, is_grouped_asset=False):
		if not row.asset_location:
			frappe.throw(_("Row {0}: Enter location for the asset item {1}").format(row.idx, row.item_code))

		item_data = frappe.db.get_value(
			"Item", row.item_code, ["asset_naming_series", "asset_category"], as_dict=1
		)
		asset_quantity = row.qty if is_grouped_asset else 1
		purchase_amount = flt(row.valuation_rate) * asset_quantity

		asset = frappe.get_doc(
			{
				"doctype": "Asset",
				"item_code": row.item_code,
				"asset_name": row.item_name,
				"naming_series": item_data.get("asset_naming_series") or "AST",
				"asset_category": item_data.get("asset_category"),
				"location": row.asset_location,
				"company": self.company,
				"supplier": self.supplier,
				"purchase_date": self.posting_date,
				"calculate_depreciation": 1,
				"purchase_receipt_amount": purchase_amount,
				"gross_purchase_amount": purchase_amount,
				"asset_quantity": asset_quantity,
				"purchase_receipt": self.name if self.doctype == "Purchase Receipt" else None,
				"purchase_invoice": self.name if self.doctype == "Purchase Invoice" else None,
				"custom_fa_credit_note": self.name if self.doctype == "FA Credit Note" else None,
				"cost_center": row.cost_center,
			}
		)

		asset.flags.ignore_validate = True
		asset.flags.ignore_mandatory = True
		asset.set_missing_values()
		asset.insert()

		return asset.name


def override_valuation(self, method=None):
    if self.doctype in ("Purchase Receipt", "Purchase Invoice", "FA Credit Note"):
        BuyingController.update_valuation_rate(self)