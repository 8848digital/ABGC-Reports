// Copyright (c) 2024, 8848digital.llp and contributors
// For license information, please see license.txt

var party_list = [];
var account_from=''
var account_to=''

frappe.ui.form.on('Multi-Party Payment Entry', {

    onload:function(frm){
        $.each(frm.doc.payment_table || [], function(i, v) {
            console.log(v.name,1111)
            frappe.model.set_value(v.doctype, v.name, "party_type",frm.doc.party)
        })
    },

    party:function(frm){
        $.each(frm.doc.payment_table || [], function(i, v) {
            console.log(v.name,1111)
            frappe.model.set_value(v.doctype, v.name, "party_type",frm.doc.party)
        })
    },

    mode_of_payment:function(frm){
        if (frm.doc.company != undefined){
            frappe.call(
                {
                    method:'abgc_reports.abgc_reports.doctype.multi_party_payment_entry.multi_party_payment_entry.get_company_account',
                    args:{
                        'mode_of_payment':frm.doc.mode_of_payment,
                        'comapny':frm.doc.company
                    },
                    callback:function(data){
                        if(frm.doc.payment_type =='Pay'){
                            $.each(frm.doc.payment_table || [], function(i, v) {
                                console.log(v.name,1111)
                                frappe.model.set_value(v.doctype, v.name, "account_paid_from",data.message)
                            })
                        }else{
                            $.each(frm.doc.payment_table || [], function(i, v) {
                                
                                frappe.model.set_value(v.doctype, v.name, "account_paid_to",data.message)
                            })
                        }
                    }
                }
            )
        }
        else{
            frm.set_value('mode_of_payment','')
            frappe.throw('Please set company');  
        }
        
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
        
        frm.fields_dict['payment_table'].grid.get_field('account_paid_from').get_query = function() {
			if (frm.doc.payment_type =='Recieve' && frm.doc.party == 'Supplier'){
                return {
                    filters: {
                        "account_type": ["in", ['Payable'] ],
                        "is_group": 0,
                        "company": frm.doc.company
                    }
                }
			}
			else if (frm.doc.payment_type =='Pay' && frm.doc.party == 'Supplier'){
                return {
                    filters: {
                        "account_type": ['in', ['Bank','Cash'] ],
                        "is_group": 0,
                        "company": frm.doc.company
                    }
                }
			}
            else if(frm.doc.payment_type =='Recieve' && frm.doc.party == 'Customer'){
                return {
                    filters: {
                        "account_type": ['in', ['Receivable'] ],
                        "is_group": 0,
                        "company": frm.doc.company
                    }
                }
			}
            else if(frm.doc.payment_type =='Pay' && frm.doc.party == 'Customer'){
                return {
                    filters: {
                        "account_type": ['in', ['Bank','Cash'] ],
                        "is_group": 0,
                        "company": frm.doc.company
                    }
                }
			}
			
        };

        frm.fields_dict['payment_table'].grid.get_field('account_paid_to').get_query = function() {
			if (frm.doc.payment_type =='Recieve' && frm.doc.party == 'Supplier'){
                return {
                    filters: {
                        "account_type": ["in", ['Bank','Cash'] ],
                        "is_group": 0,
                        "company": frm.doc.company
                    }
                }
			}
			else if (frm.doc.payment_type =='Pay' && frm.doc.party == 'Supplier'){
                return {
                    filters: {
                        "account_type": ['in', ['Payable'] ],
                        "is_group": 0,
                        "company": frm.doc.company
                    }
                }
			}
            else if(frm.doc.payment_type =='Recieve' && frm.doc.party == 'Customer'){
                return {
                    filters: {
                        "account_type": ['in', ['Bank','Cash'] ],
                        "is_group": 0,
                        "company": frm.doc.company
                    }
                }
			}
            else if(frm.doc.payment_type =='Pay' && frm.doc.party == 'Customer'){
                return {
                    filters: {
                        "account_type": ['in', ['Receivable'] ],
                        "is_group": 0,
                        "company": frm.doc.company
                    }
                }
			}
        };

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

        frm.fields_dict['payment_entry_refrence'].grid.get_field('reference_name').get_query = function(frm, cdt, cdn) {
            var filter_party_list=[]

            cur_frm.doc.payment_table.forEach(function(party_value){
                    filter_party_list.push(party_value.part_type)
            })
            
            if (cur_frm.doc.party == 'Customer'){
                return {
                    filters: { "customer": ["in", filter_party_list] , 'outstanding_amount':['>' , 0] }
                };
            }else{
                return {
                    filters: { "supplier": ["in", filter_party_list] , 'outstanding_amount':['>' , 0]}
                };
            }
            





            
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

frappe.ui.form.on('Multi Party Entry', {
    payment_table_add:function(frm,cdn,cdt){
        console.log('ddddd')
        var d = locals[cdn][cdt];
        console.log(d)
        frappe.model.set_value(d.doctype, d.name, "party_type",cur_frm.doc.party);
    }
})







