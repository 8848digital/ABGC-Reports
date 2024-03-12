import math
import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, cstr, flt, formatdate, get_first_day, getdate


from erpnext.accounts.utils import get_fiscal_year
from abgc_reports.customization.financial_statements_abgc import (
	get_fiscal_year_data,
	validate_fiscal_year,
	validate_dates,
	get_months,
	get_label,
	get_accounts,
	filter_accounts,
	get_appropriate_currency,
	set_gl_entries_by_account,
	calculate_values,
	filter_out_zero_value_rows,
	add_total_row,
	)

def get_period_list(
	from_fiscal_year,
	to_fiscal_year,
	period_start_date,
	period_end_date,
	filter_based_on,
	periodicity,
	accumulated_values=False,
	company=None,
	reset_period_on_fy_change=True,
	ignore_fiscal_year=False,
):
	"""Get a list of dict {"from_date": from_date, "to_date": to_date, "key": key, "label": label}
	Periodicity can be (Yearly, Quarterly, Monthly)"""

	if filter_based_on == "Fiscal Year":
		fiscal_year = get_fiscal_year_data(from_fiscal_year, to_fiscal_year)
		validate_fiscal_year(fiscal_year, from_fiscal_year, to_fiscal_year)
		year_start_date = getdate(fiscal_year.year_start_date)
		year_end_date = getdate(fiscal_year.year_end_date)
	else:
		validate_dates(period_start_date, period_end_date)
		year_start_date = getdate(period_start_date)
		year_end_date = getdate(period_end_date)

	months_to_add = {"Yearly": 12, "Half-Yearly": 6, "Quarterly": 3, "Monthly": 1}[periodicity]

	period_list = []

	start_date = year_start_date
	months = get_months(year_start_date, year_end_date)

	for i in range(cint(math.ceil(months / months_to_add))):
		period = frappe._dict({"from_date": start_date})

		if i == 0 and filter_based_on == "Date Range":
			to_date = add_months(get_first_day(start_date), months_to_add)
		else:
			to_date = add_months(start_date, months_to_add)

		start_date = to_date

		# Subtract one day from to_date, as it may be first day in next fiscal year or month
		to_date = add_days(to_date, -1)

		if to_date <= year_end_date:
			# the normal case
			period.to_date = to_date
		else:
			# if a fiscal year ends before a 12 month period
			period.to_date = year_end_date

		if not ignore_fiscal_year:
			period.to_date_fiscal_year = get_fiscal_year(period.to_date, company=company)[0]
			period.from_date_fiscal_year_start_date = get_fiscal_year(period.from_date, company=company)[1]

		period_list.append(period)

		if period.to_date == year_end_date:
			break

	# common processing
	for opts in period_list:
		key = opts["to_date"].strftime("%b_%Y").lower()
		if periodicity == "Monthly" and not accumulated_values:
			label = formatdate(opts["to_date"], "MMM YYYY")
		else:
			if not accumulated_values:
				label = get_label(periodicity, opts["from_date"], opts["to_date"])
			else:
				if reset_period_on_fy_change:
					label = get_label(periodicity, opts.from_date_fiscal_year_start_date, opts["to_date"])
				else:
					label = get_label(periodicity, period_list[0].from_date, opts["to_date"])

		opts.update(
			{
				"key": key.replace(" ", "_").replace("-", "_"),
				"budget_key": key.replace(" ", "_").replace("-", "_") + "_budget",
				"label": label+" Actual",
				"budget_label": label+" Budget",
				"year_start_date": year_start_date,
				"year_end_date": year_end_date,
			}
		)

	return period_list


def get_data(
	company,
	root_type,
	balance_must_be,
	custom_sub_report_type,
	period_list,
	filters=None,
	accumulated_values=1,
	only_current_fiscal_year=True,
	ignore_closing_entries=False,
	ignore_accumulated_values_for_fy=False,
	total=True,
):

	accounts = get_accounts(company, root_type,custom_sub_report_type)

	if not accounts:
		return None

	accounts, accounts_by_name, parent_children_map = filter_accounts(accounts)

	company_currency = get_appropriate_currency(company, filters)

	gl_entries_by_account = {}
	for root in frappe.db.sql(
		"""select lft, rgt, custom_sub_report_type from tabAccount
			where root_type=%s and ifnull(parent_account, '') = ''""",
		root_type,
		as_dict=1,
	):

		set_gl_entries_by_account(
			company,
			period_list[0]["year_start_date"] if only_current_fiscal_year else None,
			period_list[-1]["to_date"],
			root.lft,
			root.rgt,
			custom_sub_report_type,
			filters,
			gl_entries_by_account,
			ignore_closing_entries=ignore_closing_entries,
			root_type=root_type,
		)

	calculate_values(
		accounts_by_name,
		gl_entries_by_account,
		period_list,
		accumulated_values,
		ignore_accumulated_values_for_fy,
	)

	get_budget_values(accounts_by_name, gl_entries_by_account, period_list)
	
	accumulate_values_into_parents(accounts, accounts_by_name, period_list)
	out = prepare_data(accounts, balance_must_be, period_list, company_currency)
	out = filter_out_zero_value_rows(out, parent_children_map)

	if out and total:
		add_total_row(out, root_type, custom_sub_report_type,balance_must_be, period_list, company_currency)

	return out


				
def get_budget_values(accounts_by_name, gl_entries_by_account, period_list):
	for gl_account in gl_entries_by_account:
		account = accounts_by_name[gl_account]
		if account.is_group:
			# Budget not assigned for group accounts
			continue
		for period in period_list:
			budget_details = frappe.db.sql(f"""
				With MOTNH_LIST AS(
				SELECT DISTINCT DATE_FORMAT(date_column, '%M') AS Month_Name
				FROM (
					SELECT
						ADDDATE('{period.from_date}', INTERVAL t4*10000 + t3*1000 + t2*100 + t1*10 + t0 DAY) AS date_column
					FROM
						(SELECT 0 t0 UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9) t0,
						(SELECT 0 t1 UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9) t1,
						(SELECT 0 t2 UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9) t2,
						(SELECT 0 t3 UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9) t3,
						(SELECT 0 t4 UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4) t4
					WHERE
						ADDDATE('{period.from_date}', INTERVAL t4*10000 + t3*1000 + t2*100 + t1*10 + t0 DAY) BETWEEN '{period.from_date}' AND '{period.to_date}'
				) as dates
				)
				Select bdg_acc.account, bdg_acc.budget_amount * sum(mdp.percentage_allocation) / 100 as budget_amount
				from 
				`tabBudget` bdg
				left outer join `tabBudget Account` bdg_acc
					on bdg.name = bdg_acc.parent
				left outer join `tabMonthly Distribution Percentage` mdp
					on bdg.monthly_distribution = mdp.parent
				left outer join `tabFiscal Year` fy
					on fy.name = bdg.fiscal_year
				where 
					bdg.docstatus = 1 and
					mdp.month in (select Month_Name from MOTNH_LIST) and
					bdg_acc.account = "{account.name}" and
					"{period.from_date}" <= fy.year_end_date and
					"{period.to_date}" >= fy.year_start_date
				group by bdg_acc.account
				""", as_dict=True)
			if budget_details:
				account[period.budget_key] = flt(budget_details[0]["budget_amount"])


def accumulate_values_into_parents(accounts, accounts_by_name, period_list):
	"""accumulate children's values in parent accounts"""
	for d in reversed(accounts):
		if d.parent_account:
			for period in period_list:
				accounts_by_name[d.parent_account][period.key] = accounts_by_name[d.parent_account].get(
					period.key, 0.0
				) + d.get(period.key, 0.0)
				
				accounts_by_name[d.parent_account][period.budget_key] = accounts_by_name[d.parent_account].get(
					period.budget_key, 0.0
				) + d.get(period.budget_key, 0.0)

			accounts_by_name[d.parent_account]["opening_balance"] = accounts_by_name[d.parent_account].get(
				"opening_balance", 0.0
			) + d.get("opening_balance", 0.0)

def prepare_data(accounts, balance_must_be, period_list, company_currency):
	data = []
	year_start_date = period_list[0]["year_start_date"].strftime("%Y-%m-%d")
	year_end_date = period_list[-1]["year_end_date"].strftime("%Y-%m-%d")

	for d in accounts:
		# add to output
		has_value = False
		total = 0
		row = frappe._dict(
			{
				"account": _(d.name),
				"parent_account": _(d.parent_account) if d.parent_account else "",
				"indent": flt(d.indent),
				"year_start_date": year_start_date,
				"year_end_date": year_end_date,
				"currency": company_currency,
				"include_in_gross": d.include_in_gross,
				"account_type": d.account_type,
				"is_group": d.is_group,
				"opening_balance": d.get("opening_balance", 0.0) * (1 if balance_must_be == "Debit" else -1),
				"account_name": (
					"%s - %s" % (_(d.account_number), _(d.account_name))
					if d.account_number
					else _(d.account_name)
				),
				"custom_sub_report_type":d.custom_sub_report_type
			}
		)
		for period in period_list:
			if d.get(period.key) and balance_must_be == "Credit":
				# change sign based on Debit or Credit, since calculation is done using (debit - credit)
				d[period.key] *= -1

			row[period.key] = flt(d.get(period.key, 0.0), 3)
			row[period.budget_key] = flt(d.get(period.budget_key, 0.0), 3)

			if abs(row[period.key]) >= 0.005:
				# ignore zero values
				has_value = True
				total += flt(row[period.key])

		row["has_value"] = has_value
		row["total"] = total
		data.append(row)

	return data

def get_columns(periodicity, period_list, accumulated_values=1, company=None):
	columns = [
		{
			"fieldname": "account",
			"label": _("Account"),
			"fieldtype": "Link",
			"options": "Account",
			"width": 300,
		}
	]
	if company:
		columns.append(
			{
				"fieldname": "currency",
				"label": _("Currency"),
				"fieldtype": "Link",
				"options": "Currency",
				"hidden": 1,
			}
		)
	for period in period_list:
		columns.extend([
			{
				"fieldname": period.key,
				"label": period.label,
				"fieldtype": "Currency",
				"options": "currency",
				"width": 150,
			},
			{
				"fieldname": period.budget_key,
				"label": period.budget_label,
				"fieldtype": "Currency",
				"options": "currency",
				"width": 150,
				"not_include_in_chart": 1
			}
		])
	if periodicity != "Yearly":
		if not accumulated_values:
			columns.append(
				{
					"fieldname": "total",
					"label": _("Total"),
					"fieldtype": "Currency",
					"width": 150,
					"options": "currency",
				}
			)

	return columns
