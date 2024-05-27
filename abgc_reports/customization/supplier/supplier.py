import frappe
import json
from frappe.utils import get_link_to_form

def before_save(self, method=None):
    if not self.custom_supplier_name:
        self.custom_supplier_name = self.supplier_name
    if self.accounts:
        return
    else:
        if self.default_currency:
            create_company_accounts(self)

@frappe.whitelist()
def create_supplier(currency,doc):
    supplier_doc = json.loads(doc)
    supplier_name = supplier_doc.get('name')
    actual_supplier_name = supplier_doc.get('custom_supplier_name')
    supplier_currency = supplier_doc.get('default_currency')

    new_supplier_name = get_supplier(actual_supplier_name,supplier_name, supplier_currency)

    supplier_group = supplier_doc.get('supplier_group')

    if new_supplier_name[:-6] != supplier_group:
        new_supplier_group = get_supplier_group(supplier_group,actual_supplier_name)
    else:
        new_supplier_group = actual_supplier_name

    supplier = frappe.get_doc("Supplier",new_supplier_name)
    supplier.supplier_group = new_supplier_group
    supplier.save()
    new_supplier_link = create_new_supplier(supplier,currency)
    link = get_link_to_form('Supplier',new_supplier_link)
    return ({"link":link})

def get_supplier(actual_supplier_name,supplier_name, default_currency):
    name = f"{actual_supplier_name} - {default_currency}"
    if name != supplier_name:
        frappe.rename_doc("Supplier", supplier_name, name)
        return name
    else:
        return supplier_name

def create_new_supplier(supplier,currency):
    new_supplier_group = supplier.supplier_group
    new_supplier = frappe.copy_doc(supplier)
    new_supplier.supplier_name = f'{new_supplier_group} - {currency}'
    new_supplier.supplier_group = new_supplier_group
    new_supplier.default_currency = currency
    new_supplier.is_internal_supplier = 0
    new_supplier.accounts = []
    new_supplier.save()
    return create_address(new_supplier.name, supplier.name)

def create_address(new_supplier, old_supplier):
    address_title = frappe.db.get_value('Dynamic Link',{"link_name":old_supplier},["parent"])
    if address_title:
        address = frappe.get_doc("Address",address_title)
        address.append(
            "links",{
                'link_doctype':"Supplier",
                'link_name': new_supplier
            })
        address.save()
    return new_supplier

def get_supplier_group(parent_group, actual_supplier_name):
    supplier_group_doc = frappe.db.exists('Supplier Group',actual_supplier_name)
    if supplier_group_doc:
        return actual_supplier_name
    else:
        create_supplier_group(parent_group,actual_supplier_name)
        return actual_supplier_name

def create_supplier_group(parent_group, supplier_group_name):
    supplier_group = frappe.get_doc(doctype='Supplier Group', supplier_group_name = supplier_group_name)
    supplier_group.parent_supplier_group = parent_group
    supplier_group.save()

def create_company_accounts(self):
    accounts_by_currency = get_company_accounts(self.default_currency)
    
    if accounts_by_currency:
        company_list = frappe.get_all('Company', ['name', 'abbr'])
        
        for company in company_list:
            account = frappe.db.get_value('Account', filters={
                'account_currency': self.default_currency,
                'company': company.get('name'),
                'account_type': "Payable"
            })
            if account:
                self.append("accounts", {
                    'company': company['name'],
                    'account': account
                })

def get_company_accounts(account_currency):
    account = frappe.get_doc('Party Account Settings')
    accounts_by_currency = {currency.currency: currency.account for currency in account.supplier_account}
    return accounts_by_currency.get(account_currency)