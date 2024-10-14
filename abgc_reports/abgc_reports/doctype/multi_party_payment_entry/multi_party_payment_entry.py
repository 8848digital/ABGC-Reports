	# Copyright (c) 2024, 8848digital.llp and contributors
	# For license information, please see license.txt

import frappe
import time
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
				payment_entry.paid_from_account_currency =  value.account_currency_from
				payment_entry.paid_to_account_currency = value.account_currency_to
				
				payment_entry.base_paid_amount = value.paid_amount * value.source_exchange_rate
				payment_entry.source_exchange_rate = value.source_exchange_rate
				payment_entry.target_exchange_rate =value.source_exchange_rate
				payment_entry.base_received_amount = value.recieve_amount
		
				if self.party == 'Supplier':
					payment_entry.payment_type = self.payment_type
					payment_entry.target_exchange_rate =value.source_exchange_rate
					payment_entry.source_exchange_rate = value.source_exchange_rate
					payment_entry.base_received_amount = value.recieve_amount
				
				if self.mode_of_payment:
					payment_entry.mode_of_payment = self.mode_of_payment

				for sales in self.payment_entry_refrence:
					if self.party == 'Customer':
						sales_invoice = frappe.get_doc('Sales Invoice', sales.reference_name)
						if self.company == sales_invoice.company and value.part_type == sales_invoice.customer:
							payment_entry.append('references', {
								'reference_doctype': 'Sales Invoice',
								'reference_name': sales.reference_name,
								'allocated_amount': sales.allocated_amount,
								'total_amount':sales.grand_total,
								'outstanding_amount':sales.outstanding
							})
					else:
						pi = frappe.get_doc('Purchase Invoice', sales.reference_name)
						if self.company == pi.company and value.part_type == pi.supplier:
							payment_entry.append('references', {
								'reference_doctype': 'Purchase Invoice',
								'reference_name': sales.reference_name,
								'allocated_amount': sales.allocated_amount,
								'total_amount':sales.grand_total,
								'outstanding_amount':sales.outstanding

							})
				
				for write_off in self.writeoff:
					if write_off.party == value.part_type:
						payment_entry.total_allocated_amount = write_off.total_allocated_amount
						payment_entry.base_total_allocated_amount =write_off.total_allocated_amount_1
						payment_entry.difference_amount = write_off.difference_amount


				if len(self.payment_deduction_loss) > 0:
					for diff in self.payment_deduction_loss:
						amount=frappe.utils.flt(diff.amount)*-1
						if self.party == 'Customer':
							print('111111')
							if value.part_type == diff.party:
								payment_entry.append('deductions',{
									"account":diff.account,
									"cost_center":diff.cost_center,
									"amount": diff.amount
								})
						else:
							print('2222')
							if value.part_type == diff.party:
								payment_entry.append('deductions',{
									"account":diff.account,
									"cost_center":diff.cost_center,
									"amount": amount
								})


				print(payment_entry.as_dict())
				payment_entry.flags.ignore_validate = True
				payment_entry.save()
				# payment_entry.submit()
				frappe.db.set_value('Multi Party Entry',{"parent":self.name},{"payment_entry":payment_entry.name})
				frappe.db.commit()
				
		except Exception as e:
			frappe.db.rollback()  
			frappe.msgprint("Error: {0}".format(e))
			raise frappe.ValidationError("Payment entry creation failed, document submission aborted.")



	def validate(self):
		if self.docstatus == 0:
			doc=frappe.db.get_all('Sales Invoice',fields=['customer','company','conversion_rate'])
			for value in self.payment_table:
				for sales in doc:
					if sales['customer'] == value.part_type and sales['company'] == self.company:
						value.source_exchange_rate =  sales.conversion_rate

			for refrence in self.payment_entry_refrence:
				if refrence.allocated_amount > refrence.outstanding:
					frappe.throw('The allocated amount must not be greater than the outstanding amount' )
			
			
			
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


@frappe.whitelist(allow_guest=True)
def set_default_party_account(**kwargs):
	customer=frappe.get_doc(f'{kwargs.get("party")}',kwargs.get('party_type'))
	for accounts in customer.accounts:
		if  kwargs.get('comapny') == accounts.company:
			return accounts.account
		


@frappe.whitelist(allow_guest=True)
def get_exchange_rate(**kwargs):
	print(kwargs.get(''))
	if kwargs.get('party_type') == 'Customer':
		exchange_rate=frappe.db.get_all('Currency Exchange',filters={'from_currency': kwargs.get('from_currency'),'to_currency': kwargs.get('to_currency')},fields=['exchange_rate'])
		return exchange_rate[0].exchange_rate
	else:
		exchange_rate=frappe.db.get_all('Currency Exchange',filters={'from_currency': kwargs.get('to_currency'),'to_currency': kwargs.get('from_currency')},fields=['exchange_rate'])
		return exchange_rate[0].exchange_rate

	





			



		

		

		
		



				

		


			

		
