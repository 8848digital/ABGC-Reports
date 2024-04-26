frappe.ui.form.on('Brand', {
    setup: (frm) => {
        frm.fields_dict["brand_defaults"].grid.get_field("income_account").get_query = function(doc, cdt, cdn) {
            const row = locals[cdt][cdn];
            return {
                query: "abgc_reports.public.py.queries.get_income_account",
                filters: { company: row.company }
            }
        }
    }
});