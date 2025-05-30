# -*- coding: utf-8 -*-
from .... import misc # Relative import for misc constants

class CustomItem:
    def __init__(self):
        self.name = "Cube/Cuboid Volume"
        self.itemtype = "cube_volume"
        self.description = "Calculates volume of a cube/cuboid: Length (L) x Width (W) x Height (H)."
        
        self.captions = ['No.', 'Length (L)', 'Width (W)', 'Height (H)', 'Volume']
        self.columntypes = [misc.MEAS_NO, misc.MEAS_L, misc.MEAS_L, misc.MEAS_L, misc.MEAS_CUST]
        
        self.cust_funcs = [
            lambda data, row: data[0], # No.
            lambda data, row: data[1], # Length
            lambda data, row: data[2], # Width
            lambda data, row: data[3], # Height
            lambda data, row: data[1] * data[2] * data[3] if len(data) > 3 else 0 # Volume = L * W * H
        ]
        
        # `data` is [No., Length, Width, Height] after evaluation
        self.total_func_item = lambda data: data[1] * data[2] * data[3] if len(data) > 3 else 0
        
        self.total_func = lambda records, user_data: sum(item.total for item in records)
        
        self.itemnos_mask = ['Schedule Item No.']
        self.itemnos_mapping = [None]
        
        self.captions_udata = []
        self.columntypes_udata = []
        self.user_data_default = []
        
        self.dimensions = [[10, 15, 15, 15, 20], [False, False, False, False, False]]

    def get_text_value(self, records, user_data, itemnos):
        total_volume = self.total_func(records, user_data)
        return f"Cube/Cuboid Volume: {total_volume:.2f} (for {len(records)} items)"

    def get_item_remark(self, record_data, user_data, itemno_data):
        return f"L={record_data[1]}, W={record_data[2]}, H={record_data[3]}"
