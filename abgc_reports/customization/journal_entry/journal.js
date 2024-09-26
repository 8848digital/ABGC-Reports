frappe.ui.form.on("Journal Entry", {
    onload: function(frm) {
        
        frm.set_df_property('voucher_type', 'options', [
            'Journal Entry',
            'Inter Company Journal Entry',
            'Bank Entry',
            'Cash Entry',
            'Credit Card Entry',
            'Debit Note',
            'Credit Note',
            'Contra Entry',
            'Excise Entry',
            'Write Off Entry',
            'Opening Entry',
            'Depreciation Entry',
            'Exchange Rate Revaluation',
            'Exchange Gain Or Loss',
            'Deferred Revenue',
            'Deferred Expense',
            'Payment Entry'
        ]);
        
        frm.set_value('voucher_type', 'Journal Entry');
        console.log(frm.doc.voucher_type);
    }
});
