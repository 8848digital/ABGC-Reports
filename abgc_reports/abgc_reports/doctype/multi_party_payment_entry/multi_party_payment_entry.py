	# Copyright (c) 2024, 8848digital.llp and contributors
	# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class MultiPartyPaymentEntry(Document):
	def on_submit(self):
		try:
			frappe.db.savepoint("before_payment_entry_creation")
			for value in self.payment_table:
				payment_entry = frappe.new_doc('Payment Entry')
				payment_entry.posting_date = self.posting_date
				payment_entry.company = self.company
				payment_entry.party_type = self.party
				payment_entry.party = value.part_type
				payment_entry.paid_amount = value.paid_amount
				payment_entry.paid_from = value.account_paid_from
				payment_entry.paid_to = value.account_paid_to
				payment_entry.received_amount = value.paid_amount
				payment_entry.reference_no = self.cheque__refrence_no
				payment_entry.reference_date = self.cheque__refrence_date
				if self.party == 'Supplier':
					payment_entry.payment_type = self.payment_type

				for sales in self.payment_entry_refrence:
					if self.party == 'Customer':
						sales_invoice = frappe.get_doc('Sales Invoice', sales.reference_name)
						if self.company == sales_invoice.company and value.part_type == sales_invoice.customer:
							payment_entry.append('references', {
								'reference_doctype': 'Sales Invoice',
								'reference_name': sales.reference_name,
								'allocated_amount': sales.allocated_amount
							})
					else:
						pi = frappe.get_doc('Purchase Invoice', sales.reference_name)
						if self.company == pi.company and value.part_type == pi.supplier:
							payment_entry.append('references', {
								'reference_doctype': 'Purchase Invoice',
								'reference_name': sales.reference_name,
								'allocated_amount': sales.allocated_amount
							})

				payment_entry.save()
				row = self.append('writeoff', {})
				row.party = payment_entry.party
				row.total_allocated_amount = payment_entry.total_allocated_amount
				row.unallocated_amount = payment_entry.unallocated_amount
				row.total_allocated_amount_1 = payment_entry.base_paid_amount
				row.difference_amount = payment_entry.difference_amount
				row.save()

			frappe.db.commit()

		except Exception as e:
			frappe.db.rollback()  
			frappe.msgprint("Error: {0}".format(e))
			raise frappe.ValidationError("Payment entry creation failed, document submission aborted.")



	def validate(self):
		doc=frappe.db.get_all('Sales Invoice',fields=['customer','company','conversion_rate'])
		for value in self.payment_table:
			for sales in doc:
				if sales['customer'] == value.part_type and sales['company'] == self.company:
					value.source_exchange_rate =  sales.conversion_rate

		for refrence in self.payment_entry_refrence:
			if refrence.allocated_amount > refrence.outstanding:
				frappe.throw('The allocated amount must not be greater than the outstanding amount' )
			
		


@frappe.whitelist(allow_guest=True)
def get_company_account(**kwargs):
	doc=frappe.get_doc('Mode of Payment',kwargs.get('mode_of_payment'))
	
	for accounts in doc.accounts:
		if kwargs.get('comapny') == accounts.company:
			return  accounts.default_account






			



		

		

		
		



				

		


			

		
