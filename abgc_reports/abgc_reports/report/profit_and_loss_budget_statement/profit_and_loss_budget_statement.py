# Copyright (c) 2024, 8848digital.llp and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt
from collections import Counter

from abgc_reports.customization.financial_statements_abgc import get_filtered_list_for_consolidated_report

from abgc_reports.customization.budget_financial_statements_abgc import (
	get_columns,
	get_data,
	get_period_list,
)

def execute(filters=None):
	period_list = get_period_list(
		filters.from_fiscal_year,
		filters.to_fiscal_year,
		filters.period_start_date,
		filters.period_end_date,
		filters.filter_based_on,
		filters.periodicity,
		company=filters.company,
	)

	t_income = get_data(
		filters.company,
		"Income",
		"Credit",
		"Trading",
		period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
		ignore_accumulated_values_for_fy=True,
	)

	t_expense = get_data(
		filters.company,
		"Expense",
		"Debit",
		"Trading",
		period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
		ignore_accumulated_values_for_fy=True,
	)

	income = get_data(
		filters.company,
		"Income",
		"Credit",
		"Non-Trading",
		period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
		ignore_accumulated_values_for_fy=True,
	)

	expense = get_data(
		filters.company,
		"Expense",
		"Debit",
		"Non-Trading",
		period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
		ignore_accumulated_values_for_fy=True,
	)
	# to rename the heads of Income and Expense as Trading and Non-Trading
	if income:
		income[0]['account_name'] = "104-2-Non-Trading Income"
	if expense:
		expense[0]['account_name'] = "105-2-Non-Trading Expense"
	if t_income:
		t_income[0]['account_name'] = "104-1-Trading Income"
	if t_expense:
		t_expense[0]['account_name'] = "105-1-Trading Expense"

	net_profit_loss_t = get_net_profit_loss(
		t_income, t_expense, period_list, "Trading",filters.company, filters.presentation_currency
	) 

	net_profit_loss = get_net_profit_loss(
		income, expense, period_list, "Non-Trading",filters.company, filters.presentation_currency
	)
	
	data = []
	data.extend(t_income or [])
	data.extend(t_expense or [])
	if net_profit_loss_t:
		data.append(net_profit_loss_t)
		data.append({})
		data.append({})
	if income and net_profit_loss_t:
		income.insert(len(income)-2,net_profit_loss_t)
		net_profit_loss = get_net_profit_loss(
		income, expense, period_list, "Non-Trading",filters.company, filters.presentation_currency
	)


	data.extend(income or [])
	if not income and net_profit_loss_t:
		data.append({"account_name":_("104-2-Non-Trading Income")})
		data.append(net_profit_loss_t)
		add_income_row = net_profit_loss_t.copy()
		add_income_row["account_name"] = _("Total Income-[Non-Trading](Credit)")
		data.append(add_income_row)
		data.append({})		

	if income:
		if net_profit_loss_t:
			update_total(-2,data,net_profit_loss_t)

	data.extend(expense or [])
	if net_profit_loss:
		data.append(net_profit_loss)
	elif not net_profit_loss and net_profit_loss_t:
		profit_total = net_profit_loss_t.copy()
		profit_total["account_name"] = "'" + _("Profit for the Year") + "'"
		data.append(profit_total)



	if net_profit_loss and net_profit_loss_t:
		update_total(-1,data,net_profit_loss_t)


	columns = get_columns(
		filters.periodicity, period_list, filters.accumulated_values, filters.company
	)

	chart = get_chart_data(filters, columns, income, t_income, t_expense, expense, net_profit_loss, net_profit_loss_t)

	currency = filters.presentation_currency or frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)
	report_summary = get_report_summary(
		period_list, filters.periodicity, income, expense, t_income, t_expense, net_profit_loss, net_profit_loss_t, currency, filters
	)

	return columns, data, None, chart, report_summary

def update_total(index,data,net_profit_loss_t):
	if net_profit_loss_t:
		x= data[index]
		y = net_profit_loss_t
		key_list = list(x.keys())
		exclude_keys = ['account_name', 'account', 'warn_if_negative', 'currency','opening_balance']
		for k in key_list:
			if k not in exclude_keys:
				data[index][k] += net_profit_loss_t[k]


def get_report_summary(
	period_list, periodicity, income, expense,t_income, t_expense, net_profit_loss, net_profit_loss_t, currency, filters, consolidated=False
):
	net_income, net_expense, net_profit = 0.0, 0.0, 0.0
	t_net_income, t_net_expense, t_net_profit = 0.0, 0.0, 0.0

	# from consolidated financial statement
	if filters.get("accumulated_in_group_company"):
		period_list = get_filtered_list_for_consolidated_report(filters, period_list)

	for period in period_list:
		key = period if consolidated else period.key
		if t_income:
			t_net_income += t_income[-2].get(key)
		if t_expense:
			t_net_expense += t_expense[-2].get(key)
		if net_profit_loss_t :
			t_net_profit += net_profit_loss_t.get(key)
		if income:
			net_income += income[-2].get(key)
		if not income and net_profit_loss_t:
			net_income += net_profit_loss_t.get(key)
		if expense:
			net_expense += expense[-2].get(key)
		if net_profit_loss:
			net_profit += net_profit_loss.get(key)
		

	if len(period_list) == 1 and periodicity == "Yearly":
		t_profit_label = _("Gross Profit This Year")
		t_income_label = _("Trading Total Income This Year")
		t_expense_label = _("Trading Total Expense This Year")
		profit_label = _("Profit This Year")
		income_label = _("Total Income This Year")
		expense_label = _("Total Expense This Year")
		
	else:
		t_profit_label = _("Gross Net Profit")
		t_income_label = _("Trading Total Income")
		t_expense_label = _("Trading Total Expense")
		profit_label = _("Net Profit")
		income_label = _("Total Income")
		expense_label = _("Total Expense")
		

	return [
		{"value": t_net_income, "label": t_income_label, "datatype": "Currency", "currency": currency},
		{"type": "separator", "value": "-"},
		{"value": t_net_expense, "label": t_expense_label, "datatype": "Currency", "currency": currency},
		{"type": "separator", "value": "=", "color": "blue"},
		{
			"value": t_net_profit,
			"indicator": "Green" if t_net_profit > 0 else "Red",
			"label": t_profit_label,
			"datatype": "Currency",
			"currency": currency,
		},

		{"value": net_income , "label": income_label, "datatype": "Currency", "currency": currency},
		{"type": "separator", "value": "-"},
		{"value": net_expense, "label": expense_label, "datatype": "Currency", "currency": currency},
		{"type": "separator", "value": "=", "color": "blue"},
		{
			"value": net_profit,
			"indicator": "Green" if net_profit > 0 else "Red",
			"label": profit_label,
			"datatype": "Currency",
			"currency": currency,
		},
	]


def get_net_profit_loss(income, expense, period_list, custom_sub_report_type, company, currency=None, consolidated=False):
	total = 0
	if custom_sub_report_type == "Trading":
		net_profit_loss = {
			"account_name": "'" + _("Gross Profit for the year") + "'",
			"account": "'" + _("Gross Profit for the year") + "'",
			"warn_if_negative": True,
			"currency": currency or frappe.get_cached_value("Company", company, "default_currency"),
		}

	else:
		net_profit_loss = {
			"account_name": "'" + _("Profit for the year") + "'",
			"account": "'" + _("Profit for the year") + "'",
			"warn_if_negative": True,
			"currency": currency or frappe.get_cached_value("Company", company, "default_currency"),
		}

	has_value = False

	for period in period_list:
		key = period if consolidated else period.key
		total_income = flt(income[-2][key], 3) if income else 0
		total_expense = flt(expense[-2][key], 3) if expense else 0

		net_profit_loss[key] = total_income - total_expense

		if net_profit_loss[key]:
			has_value = True

		total += flt(net_profit_loss[key])
		net_profit_loss["total"] = total

	if has_value:
		return net_profit_loss


def get_chart_data(filters, columns, income,t_income, t_expense, expense, net_profit_loss, net_profit_loss_t):
	labels = [d.get("label") for d in columns[2:] if not d.get("not_include_in_chart")]

	t_income_data, t_expense_data, income_data, expense_data, net_profit, t_net_profit = [], [], [], [], [], []

	for p in columns[2:]:
		if t_income:
			t_income_data.append(t_income[-2].get(p.get("fieldname")))
		if t_expense:
			t_expense_data.append(t_expense[-2].get(p.get("fieldname")))
		if net_profit_loss_t:
			t_net_profit.append(net_profit_loss_t.get(p.get("fieldname")))

		if income:
			income_data.append(income[-2].get(p.get("fieldname")))
		if expense:
			expense_data.append(expense[-2].get(p.get("fieldname")))
		if net_profit_loss:
			net_profit.append(net_profit_loss.get(p.get("fieldname")))
		
	datasets = []
	if t_income_data:
		datasets.append({"name": _("Trading Income"), "values": income_data})
	if t_expense_data:
		datasets.append({"name": _("Trading Expense"), "values": expense_data})
	if t_net_profit:
		datasets.append({"name": _("Trading Net Profit/Loss"), "values": net_profit}) 

	if income_data:
		datasets.append({"name": _("Income"), "values": income_data})
	if expense_data:
		datasets.append({"name": _("Expense"), "values": expense_data})
	if net_profit:
		datasets.append({"name": _("Net Profit/Loss"), "values": net_profit})


	chart = {"data": {"labels": labels, "datasets": datasets}}

	if not filters.accumulated_values:
		chart["type"] = "bar"
	else:
		chart["type"] = "line"

	chart["fieldtype"] = "Currency"

	return chart
