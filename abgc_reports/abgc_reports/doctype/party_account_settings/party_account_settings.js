// Copyright (c) 2024, 8848digital.llp and contributors
// For license information, please see license.txt

frappe.ui.form.on('Party Account Settings', {
    onload: function(frm) {
        set_account_query(frm, 'supplier_account', 'Payable');
        set_account_query(frm, 'customer_account', 'Receivable');

        set_currency_query(frm, 'supplier_account');
        set_currency_query(frm, 'customer_account');
    },
    supplier_account_add: function(frm, cdt, cdn) {
		let child = locals[cdt][cdn];
        set_currency_query(frm, 'supplier_account', child);
    },
    customer_account_add: function(frm, cdt, cdn) {
		let child = locals[cdt][cdn];
        set_currency_query(frm, 'customer_account',child);
    }
});

function set_account_query(frm, table_name, account_type) {
    frm.fields_dict[table_name].grid.get_field('account').get_query = function(doc, cdt, cdn) {
        var child = locals[cdt][cdn];
        return {
            filters: {
                'account_currency': child.currency,
                'company': frm.doc.company,
                'account_type': account_type
            }
        };
    };
}

function set_currency_query(frm, table_name, child = null) {
    frm.fields_dict[table_name].grid.get_field('currency').get_query = function() {
        let selected_currencies = [];
        $.each(frm.doc[table_name], function(index, row) {
			
            if (row.currency && (!child || row.name !== child.name)) {
                selected_currencies.push(row.currency);
            }
        });

        return {
            filters: [
                ['Currency', 'name', 'not in', selected_currencies]
            ]
        };
    };
}