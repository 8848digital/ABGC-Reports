# Copyright (c) 2024, 8848digital.llp and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import add_days, cstr, flt, formatdate, getdate
from collections import defaultdict
from erpnext.accounts.report.utils import convert


import erpnext
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
	get_dimension_with_children,
)
from abgc_reports.abgc_reports.report.financial_statements import (
	filter_out_zero_value_rows,
	get_account_heads
)
from erpnext.accounts.report.financial_statements import (
	get_fiscal_year_data,
)

# from frappe.query_builder import Criterion
from frappe.utils import cint, flt, getdate

from erpnext.accounts.report.utils import convert_to_presentation_currency, get_currency

v = []

for c in frappe.db.get_all('Company', pluck = 'name'):
	v.append(f"{c}-closing_debit")
	v.append(f"{c}-closing_credit")
	v.append(f"{c}-opening_debit")
	v.append(f"{c}-opening_credit")


def execute(filters=None):
	validate_filters(filters)
	companies = get_companies(filters)
	data = get_data(filters, companies)
	columns = get_columns(filters, companies)
	return columns, data

def get_companies(filters):
	if filters.consolidated:
		companies= frappe.db.get_list("Company",{"parent_company":filters.company},pluck='name')
		companies.insert(0, filters.company)
		return companies

def validate_filters(filters):
	if not filters.fiscal_year:
		frappe.throw(_("Fiscal Year {0} is required").format(filters.fiscal_year))

	fiscal_year = frappe.get_cached_value(
		"Fiscal Year", filters.fiscal_year, ["year_start_date", "year_end_date"], as_dict=True
	)
	if not fiscal_year:
		frappe.throw(_("Fiscal Year {0} does not exist").format(filters.fiscal_year))
	else:
		filters.year_start_date = getdate(fiscal_year.year_start_date)
		filters.year_end_date = getdate(fiscal_year.year_end_date)

	if not filters.from_date:
		filters.from_date = filters.year_start_date

	if not filters.to_date:
		filters.to_date = filters.year_end_date

	filters.from_date = getdate(filters.from_date)
	filters.to_date = getdate(filters.to_date)

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date cannot be greater than To Date"))

	if (filters.from_date < filters.year_start_date) or (filters.from_date > filters.year_end_date):
		frappe.msgprint(
			_("From Date should be within the Fiscal Year. Assuming From Date = {0}").format(
				formatdate(filters.year_start_date)
			)
		)

		filters.from_date = filters.year_start_date

	if (filters.to_date < filters.year_start_date) or (filters.to_date > filters.year_end_date):
		frappe.msgprint(
			_("To Date should be within the Fiscal Year. Assuming To Date = {0}").format(
				formatdate(filters.year_end_date)
			)
		)
		filters.to_date = filters.year_end_date

	if filters.company:
		is_group = frappe.db.get_value("Company",filters.company,"is_group")
		if not is_group and filters.consolidated:
			frappe.throw("Cannot consolidate the report for child company.")

def get_data(filters, companies):
	if filters.consolidated:
		total_row = {
				"account": "'" + _("Total") + "'",
				"account_name": "'" + _("Total") + "'",
				"warn_if_negative": True,
			}
		for key in v:
			total_row.update({key:0.0})

		fiscal_year = get_fiscal_year_data(filters.get("from_fiscal_year"), filters.get("to_fiscal_year"))
		accounts, accounts_by_name, parent_children_map = get_account_heads(companies, filters)

		if not accounts:
			return None
		
		company_currency = get_company_currency(filters)
		if filters.filter_based_on == "Fiscal Year":
			start_date = fiscal_year.year_start_date if filters.report != "Balance Sheet" else None
			end_date = fiscal_year.year_end_date
		else:
			start_date = filters.period_start_date if filters.report != "Balance Sheet" else None
			end_date = filters.period_end_date

		opening_balances = get_companywise_opening_balances(filters, companies)

		gl_entries_by_account = {}

		set_gl_entries_by_account(
			start_date,
			end_date,
			filters,
			gl_entries_by_account,
			accounts_by_name,
			accounts,
		)

		calculate_value(accounts, companies,gl_entries_by_account,accounts_by_name,opening_balances,filters.get("show_net_values"))

		cfs_accumulate_values_into_parents(accounts, accounts_by_name, companies)
		
		data = prepare_data(accounts, filters, company_currency, companies)
		
		data = filter_out_zero_value_rows(
			data, parent_children_map, show_zero_values=filters.get("show_zero_values")
		)

		calculate_total(data, total_row, companies)
		data.extend([{}, total_row])

		return data
	else:
		return None

def cfs_accumulate_values_into_parents(accounts, accounts_by_name, companies):
	"""accumulate children's values in parent accounts"""
	for d in reversed(accounts):
		if d.parent_account:
			account = d.parent_account_name

			for company in companies:
				for key in ["-closing_debit","-closing_credit","-opening_debit","-opening_credit"]:
					accounts_by_name[account][company+key] = accounts_by_name[account].get(company+key, 0.0) + d.get(
						company+key, 0.0
					)


def calculate_value(accounts, companies,gl_entries_by_account,accounts_by_name,opening_balances,show_net_values):

	for account_name, gl_list in gl_entries_by_account.items():
		init = {}
		for company in companies:
			debit = credit = 0
			abbr = frappe.db.get_value("Company",company,"abbr")
			init[company+"-opening_debit"] = opening_balances.get(company,{}).get(account_name+" - "+abbr, {}).get("opening_debit", 0)
			init[company+"-opening_credit"] = opening_balances.get(company,{}).get(account_name+" - "+abbr, {}).get("opening_credit", 0)

			for entry in gl_list:
				if entry.get("company") == company:
					if cstr(entry.is_opening) != "Yes":
						debit += flt(entry.debit)
						credit += flt(entry.credit)

			init[company+"-closing_debit"] = init[company+"-opening_debit"] + debit
			init[company+"-closing_credit"] = init[company+"-opening_credit"] + credit

		name = accounts_by_name.get(account_name,{}).get("name")

		for account in accounts:
			if account.name == name:
				account.update(init)
				if show_net_values:
					prepare_opening_closing(account,companies)
				break
			

def prepare_data(accounts, filters, company_currency, companies):
	data = []

	for d in accounts:
		# Prepare opening closing for group account
		# if parent_children_map.get(d.account) and filters.get("show_net_values"):
		# 	prepare_opening_closing(d)

		has_value = False
		row = {
			"account": d.name,
			"parent_account": d.parent_account,
			"indent": d.indent,
			"from_date": filters.from_date,
			"to_date": filters.to_date,
			"currency": company_currency,
			"account_name": (
				"{} - {}".format(d.account_number, d.account_name) if d.account_number else d.account_name
			),
		}

		for key in v:
			row[key] = flt(d.get(key, 0.0), 3)

			if abs(row[key]) >= 0.005:
				# ignore zero values
				has_value = True

		row["has_value"] = has_value
		data.append(row)

	return data

def calculate_total(data, total_row, companies):

	for d in data:
		if not d.get("parent_account"):
			for company in companies:
				for field in [company+"-closing_debit",company+"-closing_credit"]:
					if d.get(field):
						total_row[field] += flt(d[field])

	return total_row

def set_gl_entries_by_account(
	from_date,
	to_date,
	filters,
	gl_entries_by_account,
	accounts_by_name,
	accounts,
	ignore_closing_entries=False,
	root_type=None,
):
	
	"""Returns a dict like { "account": [gl entries], ... }"""

	company_lft, company_rgt = frappe.db.get_value(
		"Company", filters.get("company"), ["lft", "rgt"]
	)

	companies = frappe.db.sql(
		""" select name, default_currency from `tabCompany`
		where lft >= %(company_lft)s and rgt <= %(company_rgt)s""",
		{
			"company_lft": company_lft,
			"company_rgt": company_rgt,
		},
		as_dict=1,
	)
	# print(f"\n\n\ncmp====>{filters.get('company'),}\n\nn")
	currency_info = frappe._dict(
		{"report_date": to_date, "presentation_currency": filters.get("presentation_currency")}
	)
	
	for d in companies:
		min_lft, max_rgt = frappe.db.sql(
		"""select min(lft), max(rgt) from `tabAccount`
		where company=%s""",
		(d.name,),
		)[0]

		gle = frappe.qb.DocType("GL Entry")
		account = frappe.qb.DocType("Account")
		query = (
			frappe.qb.from_(gle)
			.inner_join(account)
			.on(account.name == gle.account)
			.select(
				gle.posting_date,
				gle.account,
				gle.debit,
				gle.credit,
				gle.is_opening,
				gle.company,
				gle.fiscal_year,
				gle.debit_in_account_currency,
				gle.credit_in_account_currency,
				gle.account_currency,
				account.account_name,
				account.account_number,
			)
			.where(
				(gle.company == d.name)
				& (gle.is_cancelled == 0)
				# & (gle.posting_date <= to_date)
				& (account.lft >= min_lft)
				& (account.rgt <= max_rgt)
			)
			.orderby(gle.account, gle.posting_date)
		)

		# if root_type:
		# 	query = query.where(account.root_type == root_type)
		# additional_conditions = get_additional_conditions(from_date, ignore_closing_entries, filters, d)
		# if additional_conditions:
		# 	query = query.where(Criterion.all(additional_conditions))
		gl_entries = query.run(as_dict=True)

		# if filters and filters.get("presentation_currency") != d.default_currency:
		# 	currency_info["company"] = d.name
		# 	currency_info["company_currency"] = d.default_currency
		# 	convert_to_presentation_currency(gl_entries, currency_info)

		for entry in gl_entries:
			if entry.account_number:
				account_name = entry.account_number + " - " + entry.account_name
			else:
				account_name = entry.account_name

			validate_entries(account_name, entry, accounts_by_name, accounts)
			gl_entries_by_account.setdefault(account_name, []).append(entry)

	return gl_entries_by_account

def get_additional_conditions(from_date, ignore_closing_entries, filters, d):
	gle = frappe.qb.DocType("GL Entry")
	additional_conditions = []

	if ignore_closing_entries:
		additional_conditions.append((gle.voucher_type != "Period Closing Voucher"))

	if from_date:
		additional_conditions.append(gle.posting_date >= from_date)

	finance_books = []
	finance_books.append("")
	if filter_fb := filters.get("finance_book"):
		finance_books.append(filter_fb)

	if filters.get("include_default_book_entries"):
		if company_fb := frappe.get_cached_value("Company", d.name, "default_finance_book"):
			finance_books.append(company_fb)

		additional_conditions.append((gle.finance_book.isin(finance_books)) | gle.finance_book.isnull())
	else:
		additional_conditions.append((gle.finance_book.isin(finance_books)) | gle.finance_book.isnull())

	return additional_conditions

def get_account_details(account):
	return frappe.get_cached_value(
		"Account",
		account,
		[
			"name",
			"report_type",
			"root_type",
			"company",
			"is_group",
			"account_name",
			"account_number",
			"parent_account",
			"lft",
			"rgt",
		],
		as_dict=1,
	)

def validate_entries(key, entry, accounts_by_name, accounts):
	# If an account present in the child company and not in the parent company
	if key not in accounts_by_name:
		args = get_account_details(entry.account)

		if args.parent_account:
			parent_args = get_account_details(args.parent_account)

			args.update(
				{
					"lft": parent_args.lft + 1,
					"rgt": parent_args.rgt - 1,
					"indent": 3,
					"root_type": parent_args.root_type,
					"report_type": parent_args.report_type,
					"parent_account_name": parent_args.account_name,
					"company_wise_opening_bal": defaultdict(float),
				}
			)

		accounts_by_name.setdefault(key, args)

		idx = len(accounts)
		# To identify parent account index
		for index, row in enumerate(accounts):
			if row.parent_account_name == args.parent_account_name:
				idx = index
				break

		accounts.insert(idx + 1, args)

def get_company_currency(filters=None):
	return filters.get("presentation_currency") or frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)

def get_companywise_opening_balances(filters, companies):
	all_opening_balances = frappe._dict()
	for company in companies:
		# filters.company = company
		opening_balances = get_opening_balances(filters, company)
		all_opening_balances.setdefault(company,opening_balances)

	return all_opening_balances

def get_opening_balances(filters, company):
	balance_sheet_opening = get_rootwise_opening_balances(filters, company, "Balance Sheet")
	pl_opening = get_rootwise_opening_balances(filters, company, "Profit and Loss")

	balance_sheet_opening.update(pl_opening)
	return balance_sheet_opening

def get_rootwise_opening_balances(filters, company, report_type):
	gle = []

	last_period_closing_voucher = ""
	ignore_closing_balances = frappe.db.get_single_value(
		"Accounts Settings", "ignore_account_closing_balance"
	)

	if not ignore_closing_balances:
		last_period_closing_voucher = frappe.db.get_all(
			"Period Closing Voucher",
			filters={"docstatus": 1, "company": company, "posting_date": ("<", filters.from_date)},
			fields=["posting_date", "name"],
			order_by="posting_date desc",
			limit=1,
		)

	accounting_dimensions = get_accounting_dimensions(as_list=False)

	if last_period_closing_voucher:
		gle = get_opening_balance(
			"Account Closing Balance",
			filters,
			company,
			report_type,
			accounting_dimensions,
			period_closing_voucher=last_period_closing_voucher[0].name,
		)

		# Report getting generate from the mid of a fiscal year
		if getdate(last_period_closing_voucher[0].posting_date) < getdate(
			add_days(filters.from_date, -1)
		):
			start_date = add_days(last_period_closing_voucher[0].posting_date, 1)
			gle += get_opening_balance(
				"GL Entry", filters,company, report_type, accounting_dimensions, start_date=start_date
			)
	else:
		gle = get_opening_balance("GL Entry", filters, company, report_type, accounting_dimensions)

	opening = frappe._dict()
	for d in gle:
		opening.setdefault(
			d.account,
			{
				"account": d.account,
				"opening_debit": 0.0,
				"opening_credit": 0.0,
			},
		)
		opening[d.account]["opening_debit"] += flt(d.debit)
		opening[d.account]["opening_credit"] += flt(d.credit)

	return opening

def get_opening_balance(
	doctype, filters, company, report_type, accounting_dimensions, period_closing_voucher=None, start_date=None
):

	closing_balance = frappe.qb.DocType(doctype)
	account = frappe.qb.DocType("Account")

	opening_balance = (
		frappe.qb.from_(closing_balance)
		.select(
			closing_balance.account,
			closing_balance.account_currency,
			Sum(closing_balance.debit).as_("debit"),
			Sum(closing_balance.credit).as_("credit"),
			Sum(closing_balance.debit_in_account_currency).as_("debit_in_account_currency"),
			Sum(closing_balance.credit_in_account_currency).as_("credit_in_account_currency"),
		)
		.where(
			(closing_balance.company == company)
			& (
				closing_balance.account.isin(
					frappe.qb.from_(account).select("name").where(account.report_type == report_type)
				)
			)
		)
		.groupby(closing_balance.account)
	)

	if period_closing_voucher:
		opening_balance = opening_balance.where(
			closing_balance.period_closing_voucher == period_closing_voucher
		)
	else:
		if start_date:
			opening_balance = opening_balance.where(
				(closing_balance.posting_date >= start_date)
				& (closing_balance.posting_date < filters.from_date)
			)
			opening_balance = opening_balance.where(closing_balance.is_opening == "No")
		else:
			opening_balance = opening_balance.where(
				(closing_balance.posting_date < filters.from_date) | (closing_balance.is_opening == "Yes")
			)

	if doctype == "GL Entry":
		opening_balance = opening_balance.where(closing_balance.is_cancelled == 0)

	if (
		not filters.show_unclosed_fy_pl_balances
		and report_type == "Profit and Loss"
		and doctype == "GL Entry"
	):
		opening_balance = opening_balance.where(closing_balance.posting_date >= filters.year_start_date)

	if not flt(filters.with_period_closing_entry):
		if doctype == "Account Closing Balance":
			opening_balance = opening_balance.where(closing_balance.is_period_closing_voucher_entry == 0)
		else:
			opening_balance = opening_balance.where(
				closing_balance.voucher_type != "Period Closing Voucher"
			)

	if filters.cost_center:
		lft, rgt = frappe.db.get_value("Cost Center", filters.cost_center, ["lft", "rgt"])
		cost_center = frappe.qb.DocType("Cost Center")
		opening_balance = opening_balance.where(
			closing_balance.cost_center.isin(
				frappe.qb.from_(cost_center)
				.select("name")
				.where((cost_center.lft >= lft) & (cost_center.rgt <= rgt))
			)
		)

	if filters.project:
		opening_balance = opening_balance.where(closing_balance.project == filters.project)

	if filters.get("include_default_book_entries"):
		company_fb = frappe.get_cached_value("Company", company, "default_finance_book")

		if filters.finance_book and company_fb and cstr(filters.finance_book) != cstr(company_fb):
			frappe.throw(_("To use a different finance book, please uncheck 'Include Default FB Entries'"))

		opening_balance = opening_balance.where(
			(closing_balance.finance_book.isin([cstr(filters.finance_book), cstr(company_fb), ""]))
			| (closing_balance.finance_book.isnull())
		)
	else:
		opening_balance = opening_balance.where(
			(closing_balance.finance_book.isin([cstr(filters.finance_book), ""]))
			| (closing_balance.finance_book.isnull())
		)

	if accounting_dimensions:
		for dimension in accounting_dimensions:
			if filters.get(dimension.fieldname):
				if frappe.get_cached_value("DocType", dimension.document_type, "is_tree"):
					filters[dimension.fieldname] = get_dimension_with_children(
						dimension.document_type, filters.get(dimension.fieldname)
					)
					opening_balance = opening_balance.where(
						closing_balance[dimension.fieldname].isin(filters[dimension.fieldname])
					)
				else:
					opening_balance = opening_balance.where(
						closing_balance[dimension.fieldname].isin(filters[dimension.fieldname])
					)

	gle = opening_balance.run(as_dict=1)

	if filters and filters.get("presentation_currency"):
		convert_to_presentation_currency(gle, get_currency(filters))

	return gle

def prepare_opening_closing(row, companies):
	for company in companies:
		cmp = company+"-"
		dr_or_cr = "debit" if row["root_type"] in ["Asset", "Equity", "Expense"] else "credit"
		reverse_dr_or_cr = "credit" if dr_or_cr == "debit" else "debit"

		for col_type in ["opening", "closing"]:
			valid_col = cmp+col_type + "_" + dr_or_cr
			reverse_col = cmp+col_type + "_" + reverse_dr_or_cr
			row[valid_col] -= row[reverse_col]
			if row[valid_col] < 0:
				row[reverse_col] = abs(row[valid_col])
				row[valid_col] = 0.0
			else:
				row[reverse_col] = 0.0

def get_columns(filters,companies=None):
	column = [
		{
			"fieldname": "account",
			"label": _("Account"),
			"fieldtype": "Link",
			"options": "Account",
			"width": 300,
		},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1,
		}]
	if filters.consolidated:
		for company in companies:
			apply_currency_formatter = 1 if not filters.presentation_currency else 0
			currency = filters.presentation_currency
			if not currency:
				currency = erpnext.get_company_currency(company)

			column.append(
				{
					"fieldname": f"{company}-closing_debit",
					"label":  _(f"{company} Closing (Dr)"),
					"fieldtype": "Currency",
					"options": "currency",
					"width": 150,
					"apply_currency_formatter": apply_currency_formatter,
					"company_name": company,
				}
			)
			column.append(
				{
					"fieldname": f"{company}-closing_credit",
					"label": _(f"{company} Closing (Cr)"),
					"fieldtype": "Currency",
					"options": "currency",
					"width": 150,
					"apply_currency_formatter": apply_currency_formatter,
					"company_name": company,
				}
			)
	else:
		column += [
		{
			"fieldname": "opening_debit",
			"label": _("Opening (Dr)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"fieldname": "opening_credit",
			"label": _("Opening (Cr)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"fieldname": "debit",
			"label": _("Debit"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"fieldname": "credit",
			"label": _("Credit"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"fieldname": "closing_debit",
			"label": _("Closing (Dr)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"fieldname": "closing_credit",
			"label": _("Closing (Cr)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		}]

	return column








# def tb_calculate_values(accounts, gl_entries_by_account, opening_balances, show_net_values):
# 	init = {
# 		"opening_debit": 0.0,
# 		"opening_credit": 0.0,
# 		"debit": 0.0,
# 		"credit": 0.0,
# 		"closing_debit": 0.0,
# 		"closing_credit": 0.0,
# 	}

# 	for d in accounts:
# 		d.update(init.copy())

# 		# add opening
# 		d["opening_debit"] = opening_balances.get(company, {}).get(d.name, {}).get("opening_debit", 0)
# 		d["opening_credit"] = opening_balances.get(company, {}).get(d.name, {}).get("opening_credit", 0)

# 		for entry in gl_entries_by_account.get(d.name, []):
# 			if cstr(entry.is_opening) != "Yes":
# 				d["debit"] += flt(entry.debit)
# 				d["credit"] += flt(entry.credit)

# 		d["closing_debit"] = d["opening_debit"] + d["debit"]
# 		d["closing_credit"] = d["opening_credit"] + d["credit"]

# 		if show_net_values:
# 			prepare_opening_closing(d)


# def cfs_calculate_values(accounts_by_name, gl_entries_by_account, companies, filters, opening_balances, fiscal_year,show_net_values=None):
# 	init = {
# 		"opening_debit": 0.0,
# 		"opening_credit": 0.0,
# 		"debit": 0.0,
# 		"credit": 0.0,
# 	}
# 	start_date = (
# 		fiscal_year.year_start_date
# 		if filters.filter_based_on == "Fiscal Year"
# 		else filters.period_start_date
# 	)
	
# 	for entries in gl_entries_by_account.values():
# 		for entry in entries:
# 			if entry.account_number:
# 				account_name = entry.account_number + " - " + entry.account_name
# 			else:
# 				account_name = entry.account_name

# 			d = accounts_by_name.get(account_name)

# 			if d:
# 				d.update(init.copy())
# 				# debit, credit = 0, 0
# 				for company in companies:
# 					d[company+"opening_dr"] = opening_balances.get(company, {}).get(d.name, {}).get("opening_debit", 0)
# 					d[company+"opening_cr"] = opening_balances.get(company, {}).get(d.name, {}).get("opening_credit", 0)

# 					# check if posting date is within the period
# 					if (
# 						entry.company == company
# 						# or (filters.get("accumulated_in_group_company"))
# 						and entry.company in companies
# 					):
# 						parent_company_currency = erpnext.get_company_currency(d.company)
# 						child_company_currency = erpnext.get_company_currency(entry.company)

# 						######
# 						if cstr(entry.is_opening) != "Yes":
# 							debit, credit = flt(entry.debit), flt(entry.credit)

# 						if (
# 							# not filters.get("presentation_currency")
# 							entry.company != company
# 							and parent_company_currency != child_company_currency
# 							# and filters.get("accumulated_in_group_company")
# 						):
# 							debit = convert(debit, parent_company_currency, child_company_currency)#, filters.end_date)
# 							credit = convert(credit, parent_company_currency, child_company_currency)#, filters.end_date)

# 						#d[company] = d.get(company, 0.0) + flt(debit) - flt(credit)
# 						d[company+"-closing_debit"] = d[company+"opening_dr"] + d["debit"]
# 						d[company+"-closing_credit"] = d[company+"opening_cr"] + d["credit"]
	
# 						# if entry.posting_date < getdate(start_date):
# 						# 	d["company_wise_opening_bal"][company] += flt(debit) - flt(credit)

# 				if entry.posting_date < getdate(start_date):
# 					d["opening_balance"] = d.get("opening_balance", 0.0) + flt(debit) - flt(credit)

# 	# print(f"\n\n accounts_by_name==> {accounts_by_name}\n\n")
					

# def tb_accumulate_values_into_parents(accounts, accounts_by_name):
# 	for d in reversed(accounts):
# 		if d.parent_account:
# 			for key in v:
# 				accounts_by_name[d.parent_account][key] += d[key]


# def accumulate_values_into_parents(accounts, accounts_by_name, companies):
# 	# print(f"\n\n\n\n\naccounts1212, {accounts} \n\n\n\n\n")
# 	# print(f"\n\n\n\n\naccounts_by_name1212, {accounts_by_name} \n\n\n\n\n")
# 	for d in reversed(accounts):
# 		if d.parent_account:
# 			account = d.parent_account_name
# 			for company in companies:
# 				accounts_by_name[account][company] = accounts_by_name[account].get(company, 0.0) + d.get(
# 					company, 0.0
# 				)



# def prepare_data(
# 	accounts, companies, company_currency, filters
# ):
# 	data = []
# 	print(f"\n\naccount in pd==>{accounts}\n\n")
# 	for d in accounts:
# 		# add to output
# 		has_value = False
# 		total = 0
# 		row = frappe._dict(
# 			{
# 				"account_name": (
# 					"%s - %s" % (_(d.account_number), _(d.account_name))
# 					if d.account_number
# 					else _(d.account_name)
# 				),
# 				"account": _(d.name),
# 				"parent_account": _(d.parent_account),
# 				"indent": flt(d.indent),
# 				# "year_start_date": start_date,
# 				"root_type": d.root_type,
# 				# "year_end_date": end_date,
# 				"currency": filters.presentation_currency,
# 				# "company_wise_opening_bal": d.company_wise_opening_bal,
# 				# "opening_balance": d.get("opening_balance", 0.0) * (1 if balance_must_be == "Debit" else -1),
# 			}
# 		)

# 		for company in companies:
# 			# if d.get(company) and balance_must_be == "Credit":
# 			# 	# change sign based on Debit or Credit, since calculation is done using (debit - credit)
# 			# 	d[company] *= -1

# 			row[company] = flt(d.get(company, 0.0), 3)

# 			if abs(row[company]) >= 0.005:
# 				# ignore zero values
# 				has_value = True
# 				total += flt(row[company])

# 		row["has_value"] = has_value
# 		row["total"] = total

# 		data.append(row)
# 	print(f"\n\n\ndata---> {data}\n\n")
# 	return data

