// Copyright (c) 2024, 8848digital.llp and contributors
// For license information, please see license.txt



var party_list = [];
frappe.ui.form.on('Multi-Party Payment Entry', {
    onload:function(frm){
        set_party(frm)
        if (frm.is_new() && frm.doc.amended_from) {
            clear_tables_on_duplicate_and_ammend(frm)
        }
        if (frm.is_new()) {
            clear_tables_on_duplicate_and_ammend(frm)
        }

        frm.doc.payment_table.forEach(function(label){
            frm.set_currency_labels(["paid_amount"],label.account_currency_from, 'payment_table');
            frm.set_currency_labels(["recieved_amount"],label.account_currency_to, 'payment_table');
        })
    },
    party:function(frm){
        set_party(frm)
        if (!frm.doc.company) {
            frm.doc.party =''
            frm.refresh_field('party')
            frappe.throw('Please Select Company First')
        }
        if (! frm.doc.posting_date) {
            frm.doc.party =''
            frm.refresh_field('party')
            frappe.throw('Please add the posting date')
        }
    },
    mode_of_payment:function(frm,cdn,cdt){
        if (frm.doc.company){
            frappe.call(
                {
                    method:'abgc_reports.abgc_reports.doctype.multi_party_payment_entry.multi_party_payment_entry.get_company_account',
                    args:{
                        'mode_of_payment':frm.doc.mode_of_payment,
                        'company':frm.doc.company
                    },
                    callback:function(response){
                        if(frm.doc.payment_type =='Pay'){
                            $.each(frm.doc.payment_table || [], function(i, v) {
                                frappe.model.set_value(v.doctype, v.name, "account_paid_from",response.message)  
                            })
                        }else{
                            $.each(frm.doc.payment_table || [], function(i, v) {
                                frappe.model.set_value(v.doctype, v.name, "account_paid_to",response.message)
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
    payment_type:function(frm){
        clear_table(frm)
    },
    refresh: function(frm) {
        if (frm.doc['payment_deduction_loss'] && frm.doc['payment_deduction_loss'].length > 0) {
            frm.fields_dict['payment_deduction_loss'].wrapper.style.display = 'block';
        } else {
            frm.fields_dict['payment_deduction_loss'].wrapper.style.display = 'none';
        }
        frm.set_df_property('set_exchange_gainloss', 'hidden', 1)
        if (frm.doc.writeoff) {
            frm.doc.writeoff.forEach(function(loss){
                if (loss.difference_amount > 0 || loss.difference_amount < 0) {
                    frm.set_df_property('set_exchange_gainloss', 'hidden', 0)
                }else{
                    frm.set_df_property('set_exchange_gainloss', 'hidden', 1)
                }
            })
        }
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
                account_filter_payable(frm)
			}
			else if (frm.doc.payment_type =='Pay' && frm.doc.party == 'Supplier'){
                account_filter_bank_and_cash(frm)
			}
            else if(frm.doc.payment_type =='Recieve' && frm.doc.party == 'Customer'){
                account_filter_receivable(frm)
			}
            else if(frm.doc.payment_type =='Pay' && frm.doc.party == 'Customer'){
                account_filter_bank_and_cash(frm)
			}
			
        };
        frm.fields_dict['payment_table'].grid.get_field('account_paid_to').get_query = function() {
			if (frm.doc.payment_type =='Recieve' && frm.doc.party == 'Supplier'){
                account_filter_bank_and_cash(frm)
			}
			else if (frm.doc.payment_type =='Pay' && frm.doc.party == 'Supplier'){
                account_filter_payable(frm)
			}
            else if(frm.doc.payment_type =='Recieve' && frm.doc.party == 'Customer'){
                account_filter_bank_and_cash(frm)
			}
            else if(frm.doc.payment_type =='Pay' && frm.doc.party == 'Customer'){
                account_filter_receivable(frm)
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
                    filter_party_list.push(party_value.party)
            })
            if (cur_frm.doc.party == 'Customer'){
                return {
                    filters: { "customer": ["in", filter_party_list] , 'outstanding_amount':['>' , 0] , 'status':  ['!=', 'Cancelled']}
                };
            }
            else{
                return {
                    filters: { "supplier": ["in", filter_party_list] , 'outstanding_amount':['>' , 0],'status':  ['!=', 'Cancelled']}
                };
            }
        };
    },
    set_exchange_gainloss:function(frm){
        frm.set_df_property('set_exchange_gainloss', 'hidden', 1)
        frm.fields_dict['payment_deduction_loss'].wrapper.style.display = 'block';
        frm.refresh_field('payment_deduction_loss'); 
        set_exchange_gain_loss(frm)
    }
});

frappe.ui.form.on('Payment References', {
    reference_name:function(frm,cdn,cdt){
        var payment_reference=locals[cdn][cdt]
        if (frm.doc.party === 'Customer'){
            var reference_details = frappe.db.get_value(payment_reference.reference_doctype, 
                {'name': payment_reference.reference_name}, 
                ['grand_total', 'outstanding_amount', 'customer', 'currency'])
        }
        if (frm.doc.party === 'Supplier') {
            var reference_details = frappe.db.get_value(payment_reference.reference_doctype, 
                {'name': payment_reference.reference_name}, 
                ['grand_total', 'outstanding_amount', 'supplier', 'currency'])
        }
        reference_details.then(function(value){
            frappe.model.set_value(payment_reference.doctype, payment_reference.name, "grand_total",value.message.grand_total)
            frappe.model.set_value(payment_reference.doctype, payment_reference.name, "outstanding",value.message.outstanding_amount)
            if (frm.doc.party === 'Customer' ) {
                frappe.model.set_value(payment_reference.doctype, payment_reference.name, "party",value.message.customer)
                frappe.model.set_value(payment_reference.doctype, payment_reference.name, "amount_currency",value.message.currency)
            }else{
                frappe.model.set_value(payment_reference.doctype, payment_reference.name, "party",value.message.supplier)
                frappe.model.set_value(payment_reference.doctype, payment_reference.name, "amount_currency",value.message.currency)
            }
        }) 
    },

    allocated_amount: function (frm, cdn, cdt) {
        get_exchange_gain_loss_account(frm,cdn,cdt)
        if (frm.doc.writeoff) {
            frm.doc.writeoff.forEach(function(loss){
                if (loss.difference_amount > 0 || loss.difference_amount  < 0) {
                    frm.set_df_property('set_exchange_gainloss', 'hidden', 0)
                }else{
                    frm.set_df_property('set_exchange_gainloss', 'hidden', 1)
                }
            })
            }
    },
    before_payment_entry_refrence_remove:function(frm,cdn,cdt){
        get_exchange_gain_loss_account(frm,cdn,cdt)
        var party_row = locals[cdn][cdt];
            table_row_remove(frm,'writeoff',party_row.party)
            table_row_remove(frm,'payment_deduction_loss',party_row.party)
        }
        
})

frappe.ui.form.on('Multi Party Entry', {
    source_exchange_rate:function(frm,cdn,cdt){
        var party_row = locals[cdn][cdt];
        if (party_row.paid_amount) {
            frappe.model.set_value(party_row.doctype, party_row.name, "recieved_amount", party_row.paid_amount *  party_row.source_exchange_rate);
            frappe.model.set_value(party_row.doctype, party_row.name, "base_paid_amount", party_row.paid_amount *  party_row.source_exchange_rate);
        }
    },
    account_paid_from:function(frm,cdn,cdt){
        var party_row = locals[cdn][cdt];
        var accounts=frappe.db.get_value('Account', {'name': party_row.account_paid_from},['account_currency'])
        accounts.then(function(value){
            frappe.model.set_value(party_row.doctype, party_row.name, "account_currency_from",value.message.account_currency)
        })
    },
    account_paid_to:function(frm,cdn,cdt){
        var party_row = locals[cdn][cdt];
        var accounts=frappe.db.get_value('Account', {'name': party_row.account_paid_to},['account_currency'])
        accounts.then(function(value){
            frappe.model.set_value(party_row.doctype, party_row.name, "account_currency_to",value.message.account_currency)
        })
    },
    payment_table_add:function(frm,cdn,cdt){
        var party_add=locals[cdn][cdt]
        frappe.model.set_value(party_add.doctype, party_add.name, "party_type",frm.doc.party)
        if (frm.doc.mode_of_payment) {
            if (frm.doc.company != undefined){
                frappe.call(
                    {
                        method:'abgc_reports.abgc_reports.doctype.multi_party_payment_entry.multi_party_payment_entry.get_company_account',
                        args:{
                            'mode_of_payment':frm.doc.mode_of_payment,
                            'company':frm.doc.company
                        },
                        callback:function(data){
                            if(frm.doc.payment_type =='Pay'){
                                frappe.model.set_value(party_add.doctype, party_add.name, "account_paid_from",data.message)  
                            }else{
                                frappe.model.set_value(party_add.doctype, party_add.name, "account_paid_to",data.message)
                            }
                            frm.refresh_field('payment_table')
                        }
                    }
                )
            }
        }
    },
    before_payment_table_remove:function(frm,cdn,cdt){
        var party_remove = locals[cdn][cdt];
        table_row_remove(frm,'payment_entry_refrence',party_remove.party)
        table_row_remove(frm,'writeoff',party_remove.party)
        table_row_remove(frm,'payment_deduction_loss',party_remove.party)
    },
    party:function(frm,cdn,cdt){
        var party_row = locals[cdn][cdt];
        frappe.call(
            {
                method:'erpnext.accounts.doctype.payment_entry.payment_entry.get_party_details',
                args:{
                        'company': frm.doc.company,
                        'party_type': frm.doc.party,
                        'party':party_row.party,
                        'date':frm.doc.posting_date
                },
                callback:function(r){
                   if (frm.doc.payment_type =='Pay') {
                    frappe.model.set_value(party_row.doctype, party_row.name, "account_paid_to",r.message.party_account)
                   }
                   else{
                    frappe.model.set_value(party_row.doctype, party_row.name, "account_paid_from",r.message.party_account)
                   }
                }
            }
        )
    },
    recieved_amount:function(frm,cdn,cdt){
        var party_row = locals[cdn][cdt];
        if (frm.doc.party == 'Customer') {
            const childTable = frm.doc.writeoff;
            const rowToDeleteIndex = childTable.findIndex(row => row.party === party_row.party); 
        if (rowToDeleteIndex !== -1) {
            childTable.splice(rowToDeleteIndex, 1); 
            frm.refresh_field('writeoff'); 
        } 
    }
    },

    paid_amount:function(frm,cdn,cdt){
        frm.set_value('payment_entry_refrence', []);
        frm.refresh_field('payment_entry_refrence');
        frm.set_value('writeoff', []);
        frm.refresh_field('writeoff');
        frm.set_value('payment_deduction_loss', []);
        frm.refresh_field('payment_deduction_loss');
        var party_row = locals[cdn][cdt];
        if (party_row.account_currency_from == party_row.account_currency_to) {
            frappe.model.set_value(party_row.doctype, party_row.name, "recieved_amount",party_row.paid_amount) 
        }
        if (frm.doc.party == 'Supplier') {
            const childTable = frm.doc.writeoff; 
            const rowToDeleteIndex = childTable.findIndex(row => row.party === party_row.party); 
        if (rowToDeleteIndex !== -1) {
            childTable.splice(rowToDeleteIndex, 1);
            frm.refresh_field('writeoff'); 
        } 
    }
        set_exchange_rate(frm,party_row)
    },

    account_currency_from: function(frm, cdn, cdt) {
        var party_row = locals[cdn][cdt];
        frm.set_currency_labels(["paid_amount"],party_row.account_currency_from);
        set_exchange_rate(frm,party_row)
        frm.refresh_field('payment_table'); 
    },
    
    account_currency_to: function(frm, cdn, cdt) {
        var party_row = locals[cdn][cdt];
        if (party_row.account_currency_from != party_row.account_currency_to) {
            frm.set_currency_labels(["recieved_amount"],party_row.account_currency_to);
        }
        set_exchange_rate(frm,party_row)
        frm.refresh_field('payment_table');   
    },

})


frappe.ui.form.on('Payment Deduction Loss', {
    before_payment_deduction_loss_remove:function(frm,cdn,cdt){
        var exchange_loss_row = locals[cdn][cdt];
        frm.doc.writeoff.forEach(function(add_diff){
            if (add_diff.party === exchange_loss_row.party ) {
                add_diff.difference_amount = exchange_loss_row.amount
                frm.refresh_field('writeoff')
            }
            if (add_diff.difference_amount > 0 || add_diff.difference_amount < 0) {
                frm.set_df_property('set_exchange_gainloss', 'hidden', 0)
            }else{
                frm.set_df_property('set_exchange_gainloss', 'hidden', 1)
            }   
        })

    }
})

frappe.ui.form.on('Writeoff', {
    before_writeoff_remove:function(frm,cdn,cdt){
        var party_remove = locals[cdn][cdt];
        table_row_remove(frm,'payment_deduction_loss',party_remove.party)
    }
})

function remove_row_by_field_value(frm, child_table, fieldname, value_to_match) {
    if (!frm.doc[child_table]) {
        return;
    }
    let table_data = frm.doc[child_table];
    let updated_data = table_data.filter(row => row[fieldname] !== value_to_match);
    frm.set_value(child_table, updated_data);
    frm.refresh_field(child_table);
}

function set_exchange_rate(frm,party_row){
    frappe.call(
        {
            method:'abgc_reports.abgc_reports.doctype.multi_party_payment_entry.multi_party_payment_entry.get_exchange_rate',
            args:{
                'from_currency':party_row.account_currency_from,
                'to_currency':party_row.account_currency_to,
                'party_type':frm.doc.party
            },
            callback:function(data){
                frappe.model.set_value(party_row.doctype, party_row.name, "source_exchange_rate",data.message)
                frappe.model.set_value(party_row.doctype, party_row.name, "base_paid_amount", party_row.paid_amount *  party_row.source_exchange_rate);
            }
        }
    )
}

function table_row_remove(frm,table,table_remove){
    if (frm.doc[table]) {
        const childTable = frm.doc[table]; 
        const rowToDeleteIndex = childTable.findIndex(row => row.party === table_remove);
        if (rowToDeleteIndex !== -1) {
            childTable.splice(rowToDeleteIndex, 1); 
            frm.refresh_field(`${table}`); 
        }
    
    } 
}

function set_party(frm){
    $.each(frm.doc.payment_table || [], function(iteration, value) {
        frappe.model.set_value(value.doctype, value.name, "party_type",frm.doc.party)
    })
}

function account_filter_payable(frm){
    return {
        filters: {
            "account_type": ["in", ['Payable'] ],
            "is_group": 0,
            "company": frm.doc.company
        }
    }
}

function account_filter_bank_and_cash(frm){
    return {
        filters: {
            "account_type": ['in', ['Bank','Cash'] ],
            "is_group": 0,
            "company": frm.doc.company
        }
    }
}

function account_filter_receivable(frm){
    return {
        filters: {
            "account_type": ['in', ['Receivable'] ],
            "is_group": 0,
            "company": frm.doc.company
        }
    }
}

function set_exchange_gain_loss(frm){
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

function clear_table(frm){
    frm.set_value('payment_table', []);
    frm.refresh_field('payment_table');
    frm.set_value('payment_entry_refrence', []);
    frm.refresh_field('payment_entry_refrence');
    frm.set_value('writeoff', []);
    frm.refresh_field('writeoff');
    frm.set_value('payment_deduction_loss', []);
    frm.refresh_field('payment_deduction_loss');
}

function  get_exchange_gain_loss_account(frm,cdn,cdt){
    var invoice_row = locals[cdn][cdt];
    var allocated_amount = 0;
    frm.doc.payment_entry_refrence.forEach(function(fn) {
        if (invoice_row.party === fn.party) {
            allocated_amount += parseFloat(fn.allocated_amount) || 0;
        }
    });
    var party_list = []
    if (frm.doc.writeoff !== undefined) {
        frm.doc.writeoff.forEach(function(get_party) {
            party_list.push(get_party.party);
        });
    }
    frm.doc.payment_table.forEach(function(rate) {
        if (invoice_row.party === rate.party) {
            if (party_list.includes(invoice_row.party)) {
                remove_row_by_field_value(frm, 'writeoff', 'party', invoice_row.party);
            }
            var source_exchange_rate = parseFloat(rate.source_exchange_rate);
            var total_allocated_amount = allocated_amount * source_exchange_rate;
            var base_unallocated_amount = 0
            if (frm.doc.payment_type == "Pay" && total_allocated_amount < rate.paid_amount && allocated_amount < rate.recieved_amount ) {
                var base_unallocated_amount = (rate.paid_amount - total_allocated_amount) / source_exchange_rate
            }
            else if(frm.doc.payment_type == "Receive" && total_allocated_amount < rate.recieved_amount + 0 && allocated_amount < rate.paid_amount){
                var base_unallocated_amount = (rate.recieved_amount + 0 - 0 - total_allocated_amount) /source_exchange_rate ;
            }
            if (frm.doc.party === 'Supplier') {
                var main_base_unallocated = base_unallocated_amount * source_exchange_rate
                var base_party_amount = flt(total_allocated_amount) + main_base_unallocated;
                var difference_amount =  flt(rate.paid_amount) - base_party_amount ;
            }else{
                var main_base_unallocated = base_unallocated_amount * source_exchange_rate
                var base_party_amount = flt(total_allocated_amount) + main_base_unallocated;
                var difference_amount = base_party_amount - flt(rate.recieved_amount) ;
            }
            let row = frm.add_child("writeoff");
            if (frm.doc.party == 'Supplier') {
                row.currency_paid_from = rate.account_currency_to 
                row.currency_paid_to = rate.account_currency_from
            }else{
                row.currency_paid_from = rate.account_currency_from
                row.currency_paid_to = rate.account_currency_to
            }
            row.total_allocated_amount = allocated_amount;
            row.total_allocated_amount_1 = total_allocated_amount; 
            row.difference_amount = difference_amount;  
            row.unallocated_amount = base_unallocated_amount
            row.party = invoice_row.party;
            frm.refresh_field('writeoff');
        }
    });
}

function clear_tables_on_duplicate_and_ammend(frm){
    frm.set_value('payment_entry_refrence', []);
    frm.refresh_field('payment_entry_refrence');
    frm.set_value('writeoff', []);
    frm.refresh_field('writeoff');
    frm.set_value('payment_deduction_loss', []);
    frm.refresh_field('payment_deduction_loss');
}