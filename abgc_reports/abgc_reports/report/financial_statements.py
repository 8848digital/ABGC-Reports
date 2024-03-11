# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import functools
import re
from collections import defaultdict
import frappe
from frappe import _
from frappe.utils import add_days, cstr

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
	get_dimension_with_children,
)
from erpnext.accounts.report.utils import convert_to_presentation_currency, get_currency


def get_companies(filters):
	if filters.get("consolidated"):
		companies= frappe.db.get_list("Company",{"parent_company":filters.company},pluck='name')
		companies.insert(0, filters.company)
		return companies

def filter_out_zero_value_rows(data, parent_children_map, show_zero_values=False):  
    data_with_value = []
    for d in data:
        if show_zero_values or d.get("has_value"):
            data_with_value.append(d)
        else:
            # show group with zero balance, if there are balances against child
            children = [child.name for child in parent_children_map.get(d.get("account")) or []]
            if children:
                for row in data:
                    if row.get("account") in children and row.get("has_value"):
                        data_with_value.append(d)
                        break

    return data_with_value

def get_account_heads(companies, filters):
	accounts = get_accounts(companies)

	if not accounts:
		return None, None, None

	accounts = update_parent_account_names(accounts)

	accounts, accounts_by_name, parent_children_map = filter_accounts(accounts)

	return accounts, accounts_by_name, parent_children_map

def update_parent_account_names(accounts):
	"""Update parent_account_name in accounts list.

	parent_name is `name` of parent account which could have other prefix
	of account_number and suffix of company abbr. This function adds key called
	`parent_account_name` which does not have such prefix/suffix.
	"""
	name_to_account_map = {}

	for d in accounts:
		if d.account_number:
			account_name = d.account_number + " - " + d.account_name
		else:
			account_name = d.account_name
		name_to_account_map[d.name] = account_name

	for account in accounts:
		if account.parent_account:
			account["parent_account_name"] = name_to_account_map.get(account.parent_account)

	return accounts

def filter_accounts(accounts, depth=20):
	parent_children_map = {}
	accounts_by_name = {}
	for d in accounts:
		if d.account_number:
			account_name = d.account_number + " - " + d.account_name
		else:
			account_name = d.account_name
		# d["company_wise_opening_bal"] = defaultdict(float)
		accounts_by_name[account_name] = d

		parent_children_map.setdefault(d.parent_account or None, []).append(d)

	filtered_accounts = []

	def add_to_list(parent, level):
		if level < depth:
			children = parent_children_map.get(parent) or []
			sort_accounts(children, is_root=True if parent == None else False)

			for child in children:
				child.indent = level
				filtered_accounts.append(child)
				add_to_list(child.name, level + 1)

	add_to_list(None, 0)

	return filtered_accounts, accounts_by_name, parent_children_map

# def filter_accounts(accounts, depth=20): 
# 	parent_children_map = {}
# 	accounts_by_name = {}
# 	for d in accounts:
# 		accounts_by_name[d.name] = d
# 		parent_children_map.setdefault(d.parent_account or None, []).append(d)

# 	filtered_accounts = []

# 	def add_to_list(parent, level):
# 		if level < depth:
# 			children = parent_children_map.get(parent) or []
# 			sort_accounts(children, is_root=True if parent == None else False)

# 			for child in children:
# 				child.indent = level
# 				filtered_accounts.append(child)
# 				add_to_list(child.name, level + 1)

# 	add_to_list(None, 0)

# 	return filtered_accounts, accounts_by_name, parent_children_map


def sort_accounts(accounts, is_root=False, key="name"): 
	"""Sort root types as Asset, Liability, Equity, Income, Expense"""

	def compare_accounts(a, b):
		if re.split(r"\W+", a[key])[0].isdigit():
			# if chart of accounts is numbered, then sort by number
			return int(a[key] > b[key]) - int(a[key] < b[key])
		elif is_root:
			if a.report_type != b.report_type and a.report_type == "Balance Sheet":
				return -1
			if a.root_type != b.root_type and a.root_type == "Asset":
				return -1
			if a.root_type == "Liability" and b.root_type == "Equity":
				return -1
			if a.root_type == "Income" and b.root_type == "Expense":
				return -1
		else:
			# sort by key (number) or name
			return int(a[key] > b[key]) - int(a[key] < b[key])
		return 1

	accounts.sort(key=functools.cmp_to_key(compare_accounts))




def set_gl_entries_by_account(
	company,
	from_date,
	to_date,
	root_lft,
	root_rgt,
	filters,
	gl_entries_by_account,
	ignore_closing_entries=False,
	ignore_opening_entries=False,
	root_type=None,
):
	"""Returns a dict like { "account": [gl entries], ... }"""
	gl_entries = []
	if filters.get("consolidated"):
		companies = get_companies(filters)
		account_filters = {
            "company": ["IN",companies],
            "is_group": 0,
            "lft": (">=", root_lft),
            "rgt": ("<=", root_rgt),
        }
	else:
		companies = None
		account_filters = {
            "company": company,
            "is_group": 0,
            "lft": (">=", root_lft),
            "rgt": ("<=", root_rgt),
        }

	if root_type:
		account_filters.update(
			{
				"root_type": root_type,
			}
		)

	accounts_list = frappe.db.get_all(
		"Account",
		filters=account_filters,
		pluck="name",
	)

	if accounts_list:
		# For balance sheet
		ignore_closing_balances = frappe.db.get_single_value(
			"Accounts Settings", "ignore_account_closing_balance"
		)
		if not from_date and not ignore_closing_balances:
			last_period_closing_voucher = frappe.db.get_all(
				"Period Closing Voucher",
				filters={
					"docstatus": 1,
					"company": ["IN",companies] if companies else filters.company,
					"posting_date": ("<", filters["period_start_date"]),
				},
				fields=["posting_date", "name"],
				order_by="posting_date desc",
				limit=1,
			)
			if last_period_closing_voucher:
				gl_entries += get_accounting_entries(
					"Account Closing Balance",
					from_date,
					to_date,
					accounts_list,
					filters,
					ignore_closing_entries,
					last_period_closing_voucher[0].name,
					companies
				)
				from_date = add_days(last_period_closing_voucher[0].posting_date, 1)
				ignore_opening_entries = True

		gl_entries += get_accounting_entries(
			"GL Entry",
			from_date,
			to_date,
			accounts_list,
			filters,
			ignore_closing_entries,
			ignore_opening_entries=ignore_opening_entries,
			companies=companies
		)

		if filters and filters.get("presentation_currency"):
			convert_to_presentation_currency(gl_entries, get_currency(filters))

		for entry in gl_entries:
			gl_entries_by_account.setdefault(entry.account, []).append(entry)

		return gl_entries_by_account



def get_accounting_entries(
	doctype,
	from_date,
	to_date,
	accounts,
	filters,
	ignore_closing_entries,
	period_closing_voucher=None,
	ignore_opening_entries=False,
	companies=None
):
	# print(f"\n\ncomapies===>{companies}\n")
	gl_entry = frappe.qb.DocType(doctype)
	query = (
		frappe.qb.from_(gl_entry)
		.select(
			gl_entry.account,
			gl_entry.debit,
			gl_entry.credit,
			gl_entry.debit_in_account_currency,
			gl_entry.credit_in_account_currency,
			gl_entry.account_currency,
		)
		
	)
	if companies:
		
		query = query.where(gl_entry.company.isin(companies))
		query = query.select(gl_entry.company)
	else:
		query = query.where(gl_entry.company == filters.company)

	if doctype == "GL Entry":
		query = query.select(gl_entry.posting_date, gl_entry.is_opening, gl_entry.fiscal_year)
		query = query.where(gl_entry.is_cancelled == 0)
		query = query.where(gl_entry.posting_date <= to_date)

		if ignore_opening_entries:
			query = query.where(gl_entry.is_opening == "No")
	else:
		query = query.select(gl_entry.closing_date.as_("posting_date"))
		query = query.where(gl_entry.period_closing_voucher == period_closing_voucher)

	query = apply_additional_conditions(doctype, query, from_date, ignore_closing_entries, filters)
	query = query.where(gl_entry.account.isin(accounts))

	entries = query.run(as_dict=True)

	return entries


def apply_additional_conditions(doctype, query, from_date, ignore_closing_entries, filters):
	gl_entry = frappe.qb.DocType(doctype)
	accounting_dimensions = get_accounting_dimensions(as_list=False)

	if ignore_closing_entries:
		if doctype == "GL Entry":
			query = query.where(gl_entry.voucher_type != "Period Closing Voucher")
		else:
			query = query.where(gl_entry.is_period_closing_voucher_entry == 0)

	if from_date and doctype == "GL Entry":
		query = query.where(gl_entry.posting_date >= from_date)

	if filters:
		if filters.get("project"):
			if not isinstance(filters.get("project"), list):
				filters.project = frappe.parse_json(filters.get("project"))

			query = query.where(gl_entry.project.isin(filters.project))

		if filters.get("cost_center"):
			filters.cost_center = get_cost_centers_with_children(filters.cost_center)
			query = query.where(gl_entry.cost_center.isin(filters.cost_center))

		if filters.get("include_default_book_entries"):
			company_fb = frappe.get_cached_value("Company", filters.company, "default_finance_book")

			if filters.finance_book and company_fb and cstr(filters.finance_book) != cstr(company_fb):
				frappe.throw(_("To use a different finance book, please uncheck 'Include Default FB Entries'"))

			query = query.where(
				(gl_entry.finance_book.isin([cstr(filters.finance_book), cstr(company_fb), ""]))
				| (gl_entry.finance_book.isnull())
			)
		else:
			query = query.where(
				(gl_entry.finance_book.isin([cstr(filters.finance_book), ""]))
				| (gl_entry.finance_book.isnull())
			)

	if accounting_dimensions:
		for dimension in accounting_dimensions:
			if filters.get(dimension.fieldname):
				if frappe.get_cached_value("DocType", dimension.document_type, "is_tree"):
					filters[dimension.fieldname] = get_dimension_with_children(
						dimension.document_type, filters.get(dimension.fieldname)
					)

				query = query.where(gl_entry[dimension.fieldname].isin(filters[dimension.fieldname]))

	return query


def get_cost_centers_with_children(cost_centers):
	if not isinstance(cost_centers, list):
		cost_centers = [d.strip() for d in cost_centers.strip().split(",") if d]

	all_cost_centers = []
	for d in cost_centers:
		if frappe.db.exists("Cost Center", d):
			lft, rgt = frappe.db.get_value("Cost Center", d, ["lft", "rgt"])
			children = frappe.get_all("Cost Center", filters={"lft": [">=", lft], "rgt": ["<=", rgt]})
			all_cost_centers += [c.name for c in children]
		else:
			frappe.throw(_("Cost Center: {0} does not exist").format(d))

	return list(set(all_cost_centers))


def get_accounts(companies):
	accounts = []
	added_accounts = []

	for company in companies:
		for account in frappe.get_all(
			"Account",
			fields=[
				"name",
				"is_group",
				"company",
				"parent_account",
				"lft",
				"rgt",
				"root_type",
				"report_type",
				"account_name",
				"account_number",
			],
			filters={"company": company},
		):
			if account.account_number:
				account_key = account.account_number + " - " + account.account_name
			else:
				account_key = account.account_name

			if account_key not in added_accounts:
				# account["account_key"] = account_key
				accounts.append(account)
				added_accounts.append(account_key)

	return accounts