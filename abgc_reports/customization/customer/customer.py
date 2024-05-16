import frappe
import json

def before_save(self, method=None):
    if not self.custom_customer_name:
        self.custom_customer_name = self.customer_name

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
    create_new_customer(customer,currency)

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
    new_customer.save()
    create_address(new_customer.name, customer.name)

def create_address(new_customer, old_customer):
    address_title = frappe.db.get_value('Dynamic Link',{"link_name":old_customer},["parent"])
    address = frappe.get_doc("Address",address_title)

    address.append(
        "links",{
            'link_doctype':"Customer",
            'link_name': new_customer
        })
    address.save()

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