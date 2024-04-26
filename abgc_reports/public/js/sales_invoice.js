frappe.ui.form.on('Sales Invoice', {
	refresh(frm) {
        frm.set_query("income_account", "items", function() {
			return{
				query: "abgc_reports.public.py.queries.get_income_account",
				filters: {
					'company': frm.doc.company,
					"disabled": 0
				}
			}
		});
	}
});