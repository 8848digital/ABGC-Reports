	# Copyright (c) 2024, 8848digital.llp and contributors
	# For license information, please see license.txt
# cheque_reference_no
# cheque__refrence_date
import frappe
import time
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

class MultiPartyPaymentEntry(Document):
	def on_submit(self):
		try:
			for value in self.payment_table:
				if self.party == 'Customer':
					base_paid_amount=value.source_exchange_rate * value.paid_amount
				if self.party == 'Supplier':
					base_paid_amount = value.paid_amount
				if self.mode_of_payment:
					mode_of_payment = self.mode_of_payment
				else:
					mode_of_payment=''

				payment_entry = frappe.get_doc({
					'doctype': 'Payment Entry',
					'posting_date':self.posting_date,
					'company':self.company,
					'posting_date' : self.posting_date,
					'company' : self.company,
					'party_type' : self.party,
					'party' : value.party,
					'paid_amount' : value.paid_amount,
					'paid_from' : value.account_paid_from,
					'paid_to' : value.account_paid_to,
					'received_amount' : value.recieved_amount,
					'reference_no' : self.cheque_reference_no,
					'reference_date' : self.cheque_reference_date,
					'paid_from_account_currency' :  value.account_currency_from,
					'paid_to_account_currency' : value.account_currency_to,
					'source_exchange_rate' : value.source_exchange_rate,
					'payment_type':self.payment_type,
					'base_paid_amount': value.base_paid_amount,
					'mode_of_payment': mode_of_payment
				})
				
				for sales in self.payment_entry_refrence:
					if self.party == 'Customer':
						reference_doctype = 'Sales Invoice'
					elif self.party == 'Supplier':
						reference_doctype = 'Purchase Invoice'
					if value.party == sales.party:
						payment_entry.append('references', {
							'reference_doctype': reference_doctype,
							'reference_name': sales.reference_name,
							'allocated_amount': sales.allocated_amount,
							'total_amount':sales.grand_total,
							'outstanding_amount':sales.outstanding
						})
				
				for write_off in self.writeoff:
					if write_off.party == value.party:
						payment_entry.total_allocated_amount = write_off.total_allocated_amount
						payment_entry.base_total_allocated_amount =write_off.total_allocated_amount_1
						payment_entry.difference_amount = write_off.difference_amount
						
				if len(self.payment_deduction_loss) > 0:
					for diff in self.payment_deduction_loss:
							if value.party == diff.party:
								payment_entry.append('deductions',{
									"account":diff.account,
									"cost_center":diff.cost_center,
									"amount": diff.amount
								})
				payment_entry.save()
				payment_entry.submit()
				frappe.db.set_value('Multi Party Entry',{"name":value.name},{"payment_entry":payment_entry.name})
				frappe.db.set_value('Multi Party Entry',{"name":value.name},{"is_cancelled":0})

				
		except Exception as e:  
			frappe.msgprint("Error: {0}".format(e))
			raise frappe.ValidationError("Payment entry creation failed, document submission aborted.")

	def validate(self):
		if self.docstatus == 0:
			for refrence in self.payment_entry_refrence:
				if refrence.allocated_amount > refrence.outstanding:
					frappe.throw('The allocated amount must not be greater than the outstanding amount' )

			if self.amended_from:
				for checkbox in self.payment_table:
					checkbox.is_cancelled = 0
					checkbox.payment_entry = None
		
	def before_cancel(self):
		for entry in self.payment_table:
			if not entry.is_cancelled:
				payment_link = frappe.utils.get_link_to_form('Payment Entry', entry.payment_entry)
				frappe.throw(_('In row {0}. The party {1} is linked with Payment Entry {2}').format(entry.idx, entry.party, payment_link))

					
@frappe.whitelist()
def get_company_account(**kwargs):
	bank_account = frappe.get_value('Mode of Payment Account', filters={'parent': kwargs.get('mode_of_payment'), 'company': kwargs.get('company')}, fieldname='default_account')
	return bank_account

@frappe.whitelist()
def get_exchange_rate(**kwargs):
	if  kwargs.get('from_currency') != None  and kwargs.get('to_currency') != None:
		if kwargs.get('party_type') == 'Customer':
			if kwargs.get('from_currency') == kwargs.get('to_currency'):
				return 1
			else:
				exchange_rate=frappe.db.get_all('Currency Exchange',filters={'from_currency': kwargs.get('from_currency'),'to_currency': kwargs.get('to_currency')},fields=['exchange_rate','date'],order_by='date desc')
				return exchange_rate[0].exchange_rate
		else:
			if kwargs.get('from_currency') == kwargs.get('to_currency'):
				return 1
			else:
				exchange_rate=frappe.db.get_all('Currency Exchange',filters={'from_currency': kwargs.get('to_currency'),'to_currency': kwargs.get('from_currency')},fields=['exchange_rate','date'],order_by='date desc')
				return exchange_rate[0].exchange_rate
				