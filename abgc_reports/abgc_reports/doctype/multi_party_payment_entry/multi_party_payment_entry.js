// Copyright (c) 2024, 8848digital.llp and contributors
// For license information, please see license.txt

var party_list = [];
var account_from=''
var account_to=''

frappe.ui.form.on('Multi-Party Payment Entry', {

    onload:function(frm){

        frm.toggle_display("account_currency_from_to", false);
        frm.toggle_display("account_currency_to", false);
        var partys=frappe.db.get_list(`${frm.doc.party}`, {
            fields: ['name'],
            limit: 500,})
            partys.then(function(data){
            data.forEach(function(value){
                party_list.push(value.name)
            })
            frm.fields_dict["payment_table"].grid.update_docfield_property('part_type', 'options', party_list);
        })
    },

    account_currency_from:function(frm){

      if (frm.doc.account_currency_from != undefined ) {
        frm.toggle_display("account_currency_from_to", true);
      }
      
    },

    account_currency_to_2:function(frm){

        if (frm.doc.account_currency_to_2 != undefined ) {
            frm.toggle_display("account_currency_to", true);
          }
    },

    party:function(frm){
        var partys=frappe.db.get_list(`${frm.doc.party}`, {
            fields: ['name'],
            limit: 500,})
        partys.then(function(data){
            data.forEach(function(value){
                party_list.push(value.name)
            })
            frm.fields_dict["payment_table"].grid.update_docfield_property('part_type', 'options', party_list);
        })
    },

    refresh: function(frm) {
        frm.toggle_display("account_currency_from_to", true);
        frm.toggle_display("account_currency_to", true);
        frm.set_query("party", function () {
				return {
                    filters: {
                    "name": ["in", Object.keys(frappe.boot.party_account_types)],
                     }
                    }
                }
            )
        
        frm.set_query("account_currency_from", function() {
    
			var account_type=[]
			if (frm.doc.payment_type =='Recieve'){
				account_type.push('Receivable')
			}
			else if (frm.doc.payment_type =='Pay'){
				account_type.push('Bank','Cash')
			}
			else{
				account_type.push('Bank','Cash')
			}
            return {
                filters: {
                    "account_type": ["in", account_type],
                    "is_group": 0,
                    "company": frm.doc.company
                }
            };
        });

        frm.set_query("account_currency_to_2", function() {
			var account_type=[]
			if (frm.doc.payment_type =='Pay'){
				account_type.push('Receivable')
			}
			else if (frm.doc.payment_type =='Recieve'){
				account_type.push('Bank','Cash')
			}
			else{
				account_type.push('Bank','Cash')
			}
            return {
                filters: {
                    "account_type": ["in", account_type	],
                    "is_group": 0,
                    "company": frm.doc.company
                }
            };
        });

		frm.fields_dict['payment_entry_refrence'].grid.get_field('reference_doctype').get_query = function(frm, cdt, cdn) {
			var doctypes = [];
            if (cur_frm.doc.party === 'Supplier') {
                doctypes=['Journal Entry','Purchase Invoice','Purchase Order']
            }
            else{
                doctypes=["Sales Order", "Sales Invoice", "Journal Entry", "Dunning"]
            }
            return {
				filters: { "name": ["in", doctypes] }
            };
        };
    }
});

frappe.ui.form.on('Payment Refrences', {
    reference_name:function(frm,cdn,cdt){
       
        var data=locals[cdn][cdt]
        var pr=frappe.db.get_doc(`${data.reference_doctype}`,`${data.reference_name}`)
        pr.then(function(value){
            frappe.model.set_value(data.doctype, data.name, "grand_total",value.grand_total)
            frappe.model.set_value(data.doctype, data.name, "outstanding",value.outstanding_amount)
        })
    }

})







