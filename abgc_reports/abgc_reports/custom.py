import frappe
from erpnext.assets.doctype.asset.asset import get_asset_account
from frappe.utils import add_months, cint, flt, getdate, time_diff_in_hours


def create_gl_entry(self, method=None):
	if self.name:
		asset_repair = frappe.get_doc("Asset Repair", self.name)
		fixed_asset_account = get_asset_account(
			"fixed_asset_account", asset=self.asset, company=self.company
		)
		for i in asset_repair.custom_repair_cost_table:
			pii = frappe.get_doc("Purchase Invoice Item", {"parent": i.purchase_invoice})
			doc = frappe.new_doc("GL Entry")
			doc.voucher_no = self.name
			doc.voucher_type = "Asset Repair"
			doc.account = "0101.111171.0000.000.0000.0000.000 - Cost - Motor Vehicles - AD"
			doc.against_voucher_type = "Purchase Invoice"
			doc.against_voucher = i.purchase_invoice
			doc.debit = i.repair_costs
			doc.cost_center = self.cost_center
			doc.debit_in_account_currency = i.repair_costs
			doc.posting_date = getdate()
			doc.against = pii.expense_account
			doc.account_currency = "AED"
			doc.company = self.company
			doc.fiscal_year = "2024"
			doc.save(ignore_permissions=True)

			doc1 = frappe.new_doc("GL Entry")
			doc1.account = pii.expense_account
			doc1.voucher_no = self.name
			doc1.voucher_type = "Asset Repair"
			doc1.cost_center = self.cost_center
			# doc1.against_voucher_type = 'Purchase Invoice'
			doc1.against = fixed_asset_account
			doc1.credit = i.repair_costs
			doc1.posting_date = getdate()
			doc1.credit_in_account_currency = i.repair_costs
			doc1.account_currency = "AED"
			doc1.company = self.company
			doc1.fiscal_year = "2024"
			doc1.save(ignore_permissions=True)


def fetch_total_repair_cost(self, method=None):
	if self.name:
		cost = []
		asset_repair = frappe.get_doc("Asset Repair", self.name)
		for i in asset_repair.custom_repair_cost_table:
			cost.append(i.repair_costs)

		print(f"\n\n\n\n\ncost, {sum(cost)} \n\n\n\n\n")

		asset_repair.repair_cost = sum(cost)
		# asset_repair.save(ignore_permissions=True)
