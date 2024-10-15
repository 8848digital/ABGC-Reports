// Copyright (c) 2024, 8848digital.llp and contributors
// For license information, please see license.txt

var party_list = [];
var account_from=''
var account_to=''

frappe.ui.form.on('Multi-Party Payment Entry', {

    onload:function(frm){

        $.each(frm.doc.payment_table || [], function(i, v) {
            frappe.model.set_value(v.doctype, v.name, "party_type",frm.doc.party)
        })
    },

    party:function(frm){
        if (!frm.doc.company) {
            frm.doc.party =''
            frm.refresh_field('party')
            frappe.throw('Please Select Company First')
            
        }
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
        if (frm.doc['payment_deduction_loss'] && frm.doc['payment_deduction_loss'].length > 0) {
            frm.fields_dict['payment_deduction_loss'].wrapper.style.display = 'block';
        } else {
            frm.fields_dict['payment_deduction_loss'].wrapper.style.display = 'none';
        }
        frm.set_df_property('set_exchange_gainloss', 'hidden', 1)
        if (! frm.doc.writeoff === undefined) {
            frm.doc.writeoff.forEach(function(loss){
                if (loss.difference_amount > 0) {
                    frm.set_df_property('set_exchange_gainloss', 'hidden', 0)
                }else{
                    frm.set_df_property('set_exchange_gainloss', 'hidden', 1)
                }
            })
        }
        
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
    },
    set_exchange_gainloss:function(frm){
        frm.set_df_property('set_exchange_gainloss', 'hidden', 0)
      
        frm.fields_dict['payment_deduction_loss'].wrapper.style.display = 'block'; // Show the table
        frm.refresh_field('payment_deduction_loss'); 
        let writeoff=frm.doc.writeoff
        let party_list=[]
        if (frm.doc.writeoff !== undefined) {
            frm.doc.writeoff.forEach(function(d) {
                party_list.push(d.party);
            });
        }
        writeoff.forEach(function(diff){
            if (diff.difference_amount > 0 || diff.difference_amount < 0) {
                    frappe.call({
                        method: "erpnext.accounts.doctype.payment_entry.payment_entry.get_company_defaults",
                        args: {
                            company: frm.doc.company
                        },
                        callback: function(r, rt) {
                            if (party_list.includes(diff.party)) {
                                remove_row_by_field_value(frm, 'payment_deduction_loss', 'party', diff.party);
                            }
                            let row = frm.add_child("payment_deduction_loss");
                            row.account = r.message['exchange_gain_loss_account'];
                            row.cost_center = r.message['cost_center'];
                            row.amount = diff.difference_amount;
                            row.party = diff.party;
                            frm.refresh_field("payment_deduction_loss");
                            diff.difference_amount = 0
                            frm.refresh_field('writeoff')
                        }
                        
                    })
                }
            }
        )
    }
});

frappe.ui.form.on('Payment Refrences', {
    reference_name:function(frm,cdn,cdt){

        var data=locals[cdn][cdt]
        var pr=frappe.db.get_doc(`${data.reference_doctype}`,`${data.reference_name}`)
        pr.then(function(value){
            frappe.model.set_value(data.doctype, data.name, "grand_total",value.grand_total)
            frappe.model.set_value(data.doctype, data.name, "outstanding",value.outstanding_amount)
            if (frm.doc.party === 'Customer' ) {
                frappe.model.set_value(data.doctype, data.name, "party",value.customer)
                frappe.model.set_value(data.doctype, data.name, "amount_currency",value.currency)

            }else{
                frappe.model.set_value(data.doctype, data.name, "party",value.supplier_name)
                frappe.model.set_value(data.doctype, data.name, "amount_currency",value.currency)
            }
        }) 
    },
    allocated_amount: function (frm, cdn, cdt) {
        var data = locals[cdn][cdt];
        var party_list = [];
        var allocated_amount = 0;
        frm.set_df_property('set_exchange_gainloss', 'hidden', 0)
        
        if (! frm.doc.writeoff === undefined) {
            frm.doc.writeoff.forEach(function(loss){
                if (loss.difference_amount > 0) {
                    frm.set_df_property('set_exchange_gainloss', 'hidden', 0)
                }else{
                    frm.set_df_property('set_exchange_gainloss', 'hidden', 1)
                }
            })
        }
        
        frm.doc.payment_entry_refrence.forEach(function(fn) {
            if (data.party === fn.party) {
                allocated_amount += parseFloat(fn.allocated_amount) || 0;
            }
        });
    
        if (frm.doc.writeoff !== undefined) {
            frm.doc.writeoff.forEach(function(d) {
                party_list.push(d.party);
            });
        }
    
        frm.doc.payment_table.forEach(function(rate) {
            if (data.party === rate.part_type) {
                if (party_list.includes(data.party)) {
                    remove_row_by_field_value(frm, 'writeoff', 'party', data.party);
                }
                var source_exchange_rate = parseFloat(rate.source_exchange_rate) || 1;
                if (frm.doc.party === 'Supplier') {
                    var total_allocated_amount = allocated_amount * source_exchange_rate;
                    var unallocated_amount = (rate.paid_amount  -  total_allocated_amount) / source_exchange_rate;
                  
                    var base_unallocated_amount = 0
                    var base_party_amount = flt(total_allocated_amount) + base_unallocated_amount;
                    var difference_amount =  flt(rate.paid_amount) - base_party_amount ;
                }
                else{
                    var total_allocated_amount = allocated_amount * source_exchange_rate;
                    var unallocated_amount = (rate.received_amount - total_allocated_amount) / frm.doc.source_exchange_rate;
                    var base_unallocated_amount = 0
                    var base_party_amount = flt(total_allocated_amount) + base_unallocated_amount;
                    var difference_amount = base_party_amount - flt(rate.recieve_amount);
                  }
                
                let row = frm.add_child("writeoff");
                row.currency_paid_from = rate.account_currency_from
                row.currency_paid_to = rate.account_currency_to
                row.total_allocated_amount = allocated_amount.toFixed(2);
                row.total_allocated_amount_1 = total_allocated_amount.toFixed(2); 
                row.difference_amount = difference_amount.toFixed(2);  
                row.party = data.party;
                console.log(data.party)
                frm.refresh_field('writeoff');
            }
        });
    }
    
})

frappe.ui.form.on('Multi Party Entry', {
    account_paid_from:function(frm,cdn,cdt){
        var data = locals[cdn][cdt];
        console.log(data.account_paid_from)
        var account=frappe.db.get_doc('Account',`${data.account_paid_from}`)
        console.log(data.account_paid_from)
        account.then(function(value){
            frappe.model.set_value(data.doctype, data.name, "account_currency_from",value.account_currency)
        })
    },

    account_paid_to:function(frm,cdn,cdt){
        var data = locals[cdn][cdt];
        var account=frappe.db.get_doc('Account',`${data.account_paid_to}`)
        account.then(function(value){
            frappe.model.set_value(data.doctype, data.name, "account_currency_to",value.account_currency)
        })
    },

    payment_table_add:function(frm,cdn,cdt){

        var v=locals[cdn][cdt]
        frappe.model.set_value(v.doctype, v.name, "party_type",frm.doc.party)

        if (frm.doc.mode_of_payment) {
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
                                frappe.model.set_value(v.doctype, v.name, "account_paid_from",data.message)  
                            }else{
                                frappe.model.set_value(v.doctype, v.name, "account_paid_to",data.message)
                            }
                            frm.refresh_field('payment_table')
                        }
                    }
                )
            }
        }
        

    },

    part_type:function(frm,cdn,cdt){
        var d = locals[cdn][cdt];
        console.log(d)
        frappe.call(
            {
                method:'erpnext.accounts.party.get_party_account',
                args:{
                    'party_type':frm.doc.party,
                    'party':d.part_type,
                    'company':frm.doc.company
                },
                callback:function(data){
                   if (frm.doc.payment_type =='Pay') {
                    frappe.model.set_value(d.doctype, d.name, "account_paid_to",data.message)
                   }
                   else{
                    frappe.model.set_value(d.doctype, d.name, "account_paid_from",data.message)
                   }
                }
            }
        )
    },
    paid_amount:function(frm,cdn,cdt){
        var d = locals[cdn][cdt];
        if (d.account_currency_from == d.account_currency_to) {
            frappe.model.set_value(d.doctype, d.name, "recieve_amount",d.paid_amount) 
        }
       
        frappe.call(
            {
                method:'abgc_reports.abgc_reports.doctype.multi_party_payment_entry.multi_party_payment_entry.get_exchange_rate',
                args:{
                    'from_currency':d.account_currency_from,
                    'to_currency':d.account_currency_to,
                    'party_type':frm.doc.party
                },
                callback:function(data){
                    frappe.model.set_value(d.doctype, d.name, "source_exchange_rate",data.message)
                }
            }
        )
    },
    account_currency_from: function(frm, cdn, cdt) {

        var d = locals[cdn][cdt];
        frappe.db.get_doc('Currency', d.account_currency_from)
        .then(function(value) {
            var paidAmountLabel = frm.fields_dict['payment_table'].$wrapper.find("label:contains('Paid amount')");
            paidAmountLabel.next('.currency-symbol').remove();
            paidAmountLabel.after(`<label class="currency-symbol">(${value.symbol})</label>`);
        });
        frm.refresh_field('payment_table');   
    },
    
    account_currency_to: function(frm, cdn, cdt) {
        var d = locals[cdn][cdt];
        frappe.db.get_doc('Currency', d.account_currency_to)
        .then(function(value) {
            var receiveAmountLabel = frm.fields_dict['payment_table'].$wrapper.find("label:contains('Recieve Amount')");
            receiveAmountLabel.next('.currency-symbol').remove();
            receiveAmountLabel.after(`<label class="currency-symbol">(${value.symbol})</label>`);
        });
        frm.refresh_field('payment_table');   
    },
    

})



frappe.ui.form.on('Payment Deduction Loss', {

    before_payment_deduction_loss_remove:function(frm,cdn,cdt){
        var d = locals[cdn][cdt];
        console.log(d)
        frm.doc.writeoff.forEach(function(add_diff){
            if (add_diff.party === d.party ) {
                add_diff.difference_amount = d.amount
                frm.refresh_field('writeoff')
            }
        })
    }

})



function remove_row_by_field_value(frm, child_table, fieldname, value_to_match) {
    // Ensure child_table exists
    if (!frm.doc[child_table]) {
        console.error(`Child table ${child_table} does not exist.`);
        return;
    }

    // Get the current data from the child table
    let table_data = frm.doc[child_table];

    // Create a new array to hold the remaining rows
    let updated_data = [];

    // Loop through the existing rows and filter out the ones to remove
    for (let i = 0; i < table_data.length; i++) {
        if (table_data[i][fieldname] !== value_to_match) {
            updated_data.push(table_data[i]);
        }
    }

    // Clear existing rows and repopulate the child table
    frm.clear_table(child_table);

    // Add back the filtered rows
    updated_data.forEach(row => {
        let new_row = frm.add_child(child_table);
        Object.assign(new_row, row);
    });

    // Refresh the field to show the updated data
    frm.refresh_field(child_table);
    console.log(`Removed rows with ${fieldname} = ${value_to_match} if they existed.`);
}








