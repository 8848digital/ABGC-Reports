frappe.ui.form.on("Customer", {
	refresh(frm) {
        frm.add_custom_button(__('Create from Currency'), function(){
            showCurrencyDialog(frm)
        });
	},
});

function showCurrencyDialog(frm) {
    if(!frm.doc.default_currency){
        frappe.msgprint("Please set the billing currency")
    }
    else{
        let doc = frm.doc;

        let d = new frappe.ui.Dialog({
            title: 'Select Currency For New Customer',
            fields: [
                {
                    label: 'Currency',
                    fieldname: 'currency',
                    fieldtype: 'Link',
                    reqd: 1,
                    options: 'Currency',
                    get_query: function() {
                        let filters = {};
                        frappe.call({
                            method: "abgc_reports.customization.customer.customer.get_currency",
                            args: {
                                currency: doc.default_currency,
                                name: doc.custom_customer_name,
                            },
                            async: false,
                            callback: function(r) {
                                if (r.message) {
                                    filters = {
                                        filters: {
                                            'name': ['in', r.message]
                                        }
                                    };
                                }
                            }
                        });
                        return filters;
                    }
                }
            ],
            size: 'small', // small, large, extra-large
            primary_action_label: 'Create Customer',
            primary_action(values) {
                createCustomer(frm, values);
                d.hide();
            }
        });
        
        d.show();
        
    }
}

function createCustomer(frm,values){
    frappe.call({
        method: "abgc_reports.customization.customer.customer.create_customer",
        args: {
            currency: values.currency,
            doc: frm.doc
        },
        callback: function(r) {
            var msg = r.message.link
            frappe.msgprint("New customer " + msg + " has been created. Click on the customer to view details.")
        }
    });
}