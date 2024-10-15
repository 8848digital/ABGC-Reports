import frappe

def before_delete(self,method=None):
    linked_multi_party = frappe.db.exists("Multi Party Entry", {"payment_entry":self.name})
    if linked_multi_party:
        multi_party =frappe.get_doc('Multi Party Entry',linked_multi_party)
        multi_party.is_canceld  = 1 
        multi_party.save()

  

    