import frappe
from frappe import _
from  erpnext.controllers.buying_controller import (
    BuyingController, 
)
from erpnext.buying.utils import validate_for_items
    
    
def get_asset_items(self):
    if self.doctype not in ["Purchase Order", "Purchase Invoice", "Purchase Receipt", "FA Credit Note"]:
        return []
    
    return [d.item_code for d in self.items if d.is_fixed_asset]
    


def override_valuation(self, method=None):
    if self.doctype in ("Purchase Receipt", "Purchase Invoice", "FA Credit Note"):
        BuyingController.update_valuation_rate(self)