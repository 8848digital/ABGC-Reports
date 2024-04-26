import frappe

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_income_account(doctype, txt, searchfield, start, page_len, filters):
	from erpnext.controllers.queries import get_match_cond

	# income account can be any Credit account,
	# but can also be a Asset account with account_type='Income Account' in special circumstances.
	# Hence the first condition is an "OR"
	if not filters:
		filters = {}

	doctype = "Account"
	condition = ""
	if filters.get("company"):
		condition += "and tabAccount.company = %(company)s"

	condition += f"and tabAccount.disabled = {filters.get('disabled', 0)}"

	return frappe.db.sql(
		"""select tabAccount.name from `tabAccount`
			where (tabAccount.report_type = "Profit and Loss"
					or tabAccount.account_type in ("Income Account", "Temporary","Capital Work in Progress"))
				and tabAccount.is_group=0
				and tabAccount.`{key}` LIKE %(txt)s
				{condition} {match_condition}
			order by idx desc, name""".format(
			condition=condition, match_condition=get_match_cond(doctype), key=searchfield
		),
		{"txt": "%" + txt + "%", "company": filters.get("company", "")},
	)