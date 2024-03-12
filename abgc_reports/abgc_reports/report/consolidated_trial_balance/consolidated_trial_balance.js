// Copyright (c) 2024, 8848digital.llp and contributors
// For license information, please see license.txt
/* eslint-disable */
frappe.require("assets/erpnext/js/financial_statements.js", function () {
	frappe.query_reports["Consolidated Trial Balance"] = {
		filters: [
			{
				fieldname: "company",
				label: __("Company"),
				fieldtype: "Link",
				options: "Company",
				default: frappe.defaults.get_user_default("Company"),
				reqd: 1,
			},
			// {
			// 	fieldname: "consolidated",
			// 	label: __("Consolidated"),
			// 	fieldtype: "Check",
			// 	default: 1,
			// },
			{
				fieldname: "fiscal_year",
				label: __("Fiscal Year"),
				fieldtype: "Link",
				options: "Fiscal Year",
				default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today()),
				reqd: 1,
				on_change: function (query_report) {
					var fiscal_year = query_report.get_values().fiscal_year;
					if (!fiscal_year) {
						return;
					}
					frappe.model.with_doc("Fiscal Year", fiscal_year, function (r) {
						var fy = frappe.model.get_doc("Fiscal Year", fiscal_year);
						frappe.query_report.set_filter_value({
							from_date: fy.year_start_date,
							to_date: fy.year_end_date,
						});
					});
				},
			},
			{
				fieldname: "from_date",
				label: __("From Date"),
				fieldtype: "Date",
				default: frappe.defaults.get_user_default("year_start_date"),
			},
			{
				fieldname: "to_date",
				label: __("To Date"),
				fieldtype: "Date",
				default: frappe.defaults.get_user_default("year_end_date"),
			},
			{
				fieldname: "cost_center",
				label: __("Cost Center"),
				fieldtype: "Link",
				options: "Cost Center",
				get_query: function () {
					var company = frappe.query_report.get_filter_value("company");
					return {
						doctype: "Cost Center",
						filters: {
							company: company,
						},
					};
				},
			},
			{
				fieldname: "project",
				label: __("Project"),
				fieldtype: "Link",
				options: "Project",
			},
			{
				fieldname: "finance_book",
				label: __("Finance Book"),
				fieldtype: "Link",
				options: "Finance Book",
			},
			{
				fieldname: "presentation_currency",
				label: __("Currency"),
				fieldtype: "Select",
				options: erpnext.get_presentation_currency_list(),
			},
			{
				fieldname: "with_period_closing_entry",
				label: __("Period Closing Entry"),
				fieldtype: "Check",
				default: 1,
			},
			{
				fieldname: "show_zero_values",
				label: __("Show zero values"),
				fieldtype: "Check",
			},
			{
				fieldname: "show_unclosed_fy_pl_balances",
				label: __("Show unclosed fiscal year's P&L balances"),
				fieldtype: "Check",
			},
			{
				fieldname: "include_default_book_entries",
				label: __("Include Default FB Entries"),
				fieldtype: "Check",
				default: 1,
			},
			{
				fieldname: "show_net_values",
				label: __("Show net values in opening and closing columns"),
				fieldtype: "Check",
				default: 1,
			},
		],
		formatter: function (value, row, column, data, default_formatter, filter) {
			if (
				frappe.query_report.get_filter_value("selected_view") == "Growth" &&
				data &&
				column.colIndex >= 3
			) {
				//Assuming that the first three columns are s.no, account name and the very first year of the accounting values, to calculate the relative percentage values of the successive columns.
				const lastAnnualValue = row[column.colIndex - 1].content;
				const currentAnnualvalue = data[column.fieldname];
				if (currentAnnualvalue == undefined) return "NA"; //making this not applicable for undefined/null values
				let annualGrowth = 0;
				if (lastAnnualValue == 0 && currentAnnualvalue > 0) {
					//If the previous year value is 0 and the current value is greater than 0
					annualGrowth = 1;
				} else if (lastAnnualValue > 0) {
					annualGrowth = (currentAnnualvalue - lastAnnualValue) / lastAnnualValue;
				}

				const growthPercent = Math.round(annualGrowth * 10000) / 100; //calculating the rounded off percentage

				value = $(`<span>${(growthPercent >= 0 ? "+" : "") + growthPercent + "%"}</span>`);
				if (growthPercent < 0) {
					value = $(value).addClass("text-danger");
				} else {
					value = $(value).addClass("text-success");
				}
				value = $(value).wrap("<p></p>").parent().html();

				return value;
			} else if (frappe.query_report.get_filter_value("selected_view") == "Margin" && data) {
				if (column.fieldname == "account_name" && data.account_name == __("Income")) {
					//Taking the total income from each column (for all the financial years) as the base (100%)
					this.baseData = row;
				}
				if (column.colIndex >= 2) {
					//Assuming that the first two columns are s.no and account name, to calculate the relative percentage values of the successive columns.
					const currentAnnualvalue = data[column.fieldname];
					const baseValue = this.baseData[column.colIndex].content;
					if (currentAnnualvalue == undefined || baseValue <= 0) return "NA";
					const marginPercent =
						Math.round((currentAnnualvalue / baseValue) * 10000) / 100;

					value = $(`<span>${marginPercent + "%"}</span>`);
					if (marginPercent < 0) value = $(value).addClass("text-danger");
					else value = $(value).addClass("text-success");
					value = $(value).wrap("<p></p>").parent().html();
					return value;
				}
			}
			if (data && column.fieldname == "account_name") {
				value = data.account_name || value;

				if (filter && filter?.text && filter?.type == "contains") {
					if (!value.toLowerCase().includes(filter.text)) {
						return value;
					}
				}

				if (data.account) {
					column.link_onclick =
						"erpnext.financial_statements.open_general_ledger(" +
						JSON.stringify(data) +
						")";
				}
				column.is_tree = true;
			}

			value = default_formatter(value, row, column, data);

			if (data && !data.parent_account) {
				value = $(`<span>${value}</span>`);

				var $value = $(value).css("font-weight", "bold");
				if (data.warn_if_negative && data[column.fieldname] < 0) {
					$value.addClass("text-danger");
				}

				value = $value.wrap("<p></p>").parent().html();
			}

			return value;
		},
		tree: true,
		name_field: "account",
		parent_field: "parent_account",
		initial_depth: 3,
	};

	erpnext.utils.add_dimensions("Trial Balance", 6);
});
