# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from abgc_reports.abgc_reports.report.accounts_receivable_summary_abgc.accounts_receivable_summary_abgc import (
	AccountsReceivableSummary,
)


def execute(filters=None):
	try:
		args = {
			"account_type": "Payable",
			"naming_by": ["Buying Settings", "supp_master_name"],
		}
		return AccountsReceivableSummary(filters).run(args)

	except Exception:
		return ""
