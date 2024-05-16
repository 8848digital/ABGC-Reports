frappe.ui.form.on("Supplier", {
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
        let d = new frappe.ui.Dialog({
            title: 'Select Currency For New Supplier',
            fields: [
                {
                    label: 'Currency',
                    fieldname: 'currency',
                    fieldtype: 'Link',
                    options: 'Currency',
                    reqd: 1
                }
            ],
            size: 'small', // small, large, extra-large 
            primary_action_label: 'Create Supplier',
            primary_action(values) {
                createSupplier(frm,values);
                d.hide();
            }
        });
        d.show();
    }
}

function createSupplier(frm,values){
    console.log("Values",values)
    frappe.call({
        method: "abgc_reports.customization.supplier.supplier.create_supplier",
        args: {
            currency: values.currency,
            doc: frm.doc
        },
        callback: function(r) {
            
        }
    });
}