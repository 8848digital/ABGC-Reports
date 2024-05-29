frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
        frm.set_query("debit_to", function() {
			return{
				filters: {
					'company': frm.doc.company,
					'account_currency': frm.doc.currency,
                    'account_type':'Receivable',
                    'is_group': 'No'
				}
			}
		});
	},
	currency:function(frm){
		frm.set_value('debit_to','')
		frm.set_value('unrealized_profit_loss_account','')
	}
});