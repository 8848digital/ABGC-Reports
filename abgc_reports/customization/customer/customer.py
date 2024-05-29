import frappe
import json
from frappe.utils import get_link_to_form

def before_save(self, method=None):
    if not self.custom_customer_name:
        self.custom_customer_name = self.customer_name
    if self.accounts:
        return
    else:
        if self.default_currency:
            create_company_accounts(self)

@frappe.whitelist()
def create_customer(currency,doc):
    customer_doc = json.loads(doc)
    customer_name = customer_doc.get('name')
    actual_customer_name = customer_doc.get('custom_customer_name')
    customer_currency = customer_doc.get('default_currency')

    new_customer_name = get_customer(actual_customer_name,customer_name, customer_currency)

    customer_group = customer_doc.get('customer_group')

    if new_customer_name[:-6] != customer_group:
        new_customer_group = get_customer_group(customer_group,actual_customer_name)
    else:
        new_customer_group = actual_customer_name

    customer = frappe.get_doc("Customer",new_customer_name)
    customer.customer_group = new_customer_group
    customer.save()
    new_customer_link = create_new_customer(customer,currency)
    link = get_link_to_form('Customer',new_customer_link)
    return ({"link":link})

def get_customer(actual_customer_name,customer_name, default_currency):
    name = f"{actual_customer_name} - {default_currency}"
    if name != customer_name:
        frappe.rename_doc("Customer", customer_name, name)
        return name
    else:
        return customer_name

def create_new_customer(customer,currency):
    new_customer_group = customer.customer_group
    new_customer = frappe.copy_doc(customer)
    new_customer.customer_name = f'{new_customer_group} - {currency}'
    new_customer.customer_group = new_customer_group
    new_customer.default_currency = currency
    new_customer.is_internal_customer = 0
    new_customer.accounts = []
    new_customer.save()
    return create_address(new_customer.name, customer.name)

def create_address(new_customer, old_customer):
    address_title = frappe.db.get_value('Dynamic Link',{"link_name":old_customer},["parent"])
    if address_title:
        address = frappe.get_doc("Address",address_title)
        address.append(
            "links",{
                'link_doctype':"Customer",
                'link_name': new_customer
            })
        address.save()
    return new_customer

def get_customer_group(parent_group, actual_customer_name):
    customer_group_doc = frappe.db.exists('Customer Group',actual_customer_name)
    if customer_group_doc:
        return actual_customer_name
    else:
        create_customer_group(parent_group,actual_customer_name)
        return actual_customer_name

def create_customer_group(parent_group, customer_group_name):
    customer_group = frappe.get_doc(doctype='Customer Group', customer_group_name = customer_group_name)
    customer_group.parent_customer_group = parent_group
    customer_group.save()

def create_company_accounts(self):
    accounts_by_currency = get_company_accounts(self.default_currency)
    
    if accounts_by_currency:
        company_list = frappe.get_all('Company', ['name', 'abbr'])
        
        for company in company_list:
            account = frappe.db.get_value('Account', filters={
                'account_currency': self.default_currency,
                'company': company.get('name'),
                'account_type': "Receivable"
            })
            if account:
                self.append("accounts", {
                    'company': company['name'],
                    'account': account
                })

def get_company_accounts(account_currency):
    account = frappe.get_doc('Party Account Settings')
    accounts_by_currency = {currency.currency: currency.account for currency in account.customer_account}
    return accounts_by_currency.get(account_currency)

@frappe.whitelist()
def get_currency(name):
    all_currency_list = frappe.get_all('Currency',filters={'enabled':1})
    used_currency_list = frappe.get_all(
            "Customer",
            filters={'custom_customer_name': name},
            fields=["default_currency"]
        )
    
    all_currency_set = {currency['name'] for currency in all_currency_list}
    used_currency_set = {currency['default_currency'] for currency in used_currency_list}

    unused_currency_set = all_currency_set - used_currency_set
    unused_currency_list = list(unused_currency_set)

    return unused_currency_list