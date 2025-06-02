# -*- coding: utf-8 -*-
from .... import misc # Relative import for misc constants

class CustomItem:
    def __init__(self):
        self.name = "Rectangle Area"
        self.itemtype = "rectangle_area" # Filename for identification
        self.description = "Calculates area of a rectangle: Length (L) x Width (W)."
        self.display_description = "Area = Length × Width" # For UI display
        self.icon_name = "object-select-symbolic" # Example GTK stock icon

        # Parameters for each record (row) in the measurement grid
        self.captions = ['No.', 'Length (L)', 'Width (W)', 'Area']
        self.columntypes = [misc.MEAS_NO, misc.MEAS_L, misc.MEAS_L, misc.MEAS_CUST]

        # Functions for each column.
        # For input columns, it's just returning the data at that index.
        # For MEAS_CUST, it's calculating the value.
        # `data` is the list of evaluated numeric values for the current record.
        # `row` is the row number (1-indexed), not typically used in basic calculations.
        self.cust_funcs = [
            lambda data, row: data[0], # No.
            lambda data, row: data[1], # Length
            lambda data, row: data[2], # Width
            lambda data, row: data[1] * data[2] if len(data) > 2 else 0 # Area = L * W
        ]

        # Function to calculate the primary result for a single record/row
        # `data` is [No., Length, Width] after evaluation
        self.total_func_item = lambda data: data[1] * data[2] if len(data) > 2 else 0 # Area = L * W

        # Function to calculate the overall total for all records
        # `records` is a list of RecordCustom instances
        # `user_data` is for parameters affecting the whole item (not used here)
        self.total_func = lambda records, user_data: sum(item.total for item in records)

        # Defines how many schedule items can be linked (usually 1 for simple quantity)
        self.itemnos_mask = ['Schedule Item No.']
        self.itemnos_mapping = [None] # No direct mapping of schedule item props to columns

        # User data (parameters that apply to the whole measurement item, not per record)
        self.captions_udata = [] # No user data for this simple template
        self.columntypes_udata = []
        self.user_data_default = []

        # Spreadsheet export dimensions (optional, for formatting)
        self.dimensions = [[10, 20, 20, 20], [False, False, False, False]]

    def get_text_value(self, records, user_data, itemnos):
        """ Returns a string representation of the measurement for display """
        total_area = self.total_func(records, user_data)
        return f"Rectangle Area: {total_area:.2f} (for {len(records)} items)"

    def get_item_remark(self, record_data, user_data, itemno_data):
        """ Returns a remark string for a specific linked schedule item based on one record (optional) """
        return f"L={record_data[1]}, W={record_data[2]}"
