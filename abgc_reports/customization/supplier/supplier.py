import frappe
import json

def before_save(self, method=None):
    if not self.custom_supplier_name:
        self.custom_supplier_name = self.supplier_name

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
    create_new_supplier(supplier,currency)

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
    new_supplier.save()
    create_address(new_supplier.name, supplier.name)

def create_address(new_supplier, old_supplier):
    address_title = frappe.db.get_value('Dynamic Link',{"link_name":old_supplier},["parent"])
    address = frappe.get_doc("Address",address_title)

    address.append(
        "links",{
            'link_doctype':"Supplier",
            'link_name': new_supplier
        })
    address.save()

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