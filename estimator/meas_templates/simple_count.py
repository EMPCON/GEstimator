# -*- coding: utf-8 -*-
from .... import misc # Relative import for misc constants

class CustomItem:
    def __init__(self):
        self.name = "Simple Count"
        self.itemtype = "simple_count"
        self.description = "Counts number of items. Quantity is the count."
        
        # For this template, the "Description of Item" will be stored in MeasurementItem.remark
        # And "Number of Items" will be the primary result of each record.
        self.captions = ['Item Description', 'Count', 'Unit'] 
        self.columntypes = [misc.MEAS_DESC, misc.MEAS_NO, misc.MEAS_DESC] 
        
        # cust_funcs: For 'Item Description', 'Count', 'Unit'
        # 'Item Description' and 'Unit' are direct inputs for each record here.
        # 'Count' is also a direct input, but will be summed up.
        self.cust_funcs = [
            lambda data, row: data[0], # Item Description (string)
            lambda data, row: data[1], # Count (number)
            lambda data, row: data[2]  # Unit (string)
        ]
        
        # total_func_item: Calculates the value for a single record (row) that contributes to the main quantity.
        # Here, it's simply the 'Count' value from the record.
        # `data` is [ItemDescription_str, Count_eval, Unit_str] after evaluation
        self.total_func_item = lambda data: data[1] if len(data) > 1 else 0 # The 'Count'
        
        # total_func: Calculates the overall total quantity for all records.
        # It sums the 'total' (which is the 'Count') from each RecordCustom instance.
        self.total_func = lambda records, user_data: sum(item.total for item in records)
        
        # itemnos_mask: Defines how many schedule items can be linked.
        self.itemnos_mask = ['Schedule Item No.']
        self.itemnos_mapping = [None] 
        
        # User data (parameters that apply to the whole measurement item, not per record)
        self.captions_udata = [] 
        self.columntypes_udata = []
        self.user_data_default = []
        
        self.dimensions = [[30, 10, 10], [True, False, False]] # Description, Count, Unit

    def get_text_value(self, records, user_data, itemnos):
        """ Returns a string representation of the measurement for display """
        total_count = self.total_func(records, user_data)
        # Assuming the first record's description and unit are representative if multiple records exist
        desc_item = records[0].data_string[0] if records and records[0].data_string else "Items"
        unit_item = records[0].data_string[2] if records and len(records[0].data_string) > 2 and records[0].data_string[2] else "Nos."
        return f"{self.name}: {total_count} {unit_item} of '{desc_item}' (from {len(records)} entries)"

    def get_item_remark(self, record_data, user_data, itemno_data):
        """ Returns a remark string for a specific linked schedule item based on one record """
        # record_data is the string list: [ItemDescription, Count, Unit]
        return f"{record_data[1]} {record_data[2]} - {record_data[0]}"
