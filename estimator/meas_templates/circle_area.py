# -*- coding: utf-8 -*-
import math
from .... import misc # Relative import for misc constants

class CustomItem:
    def __init__(self):
        self.name = "Circle Area"
        self.itemtype = "circle_area"
        self.description = "Calculates area of a circle: π * R^2."
        self.display_description = "Area = π × Radius²" # For UI display
        self.icon_name = "draw-ellipse-symbolic" # Example GTK stock icon (if available, else another)

        self.captions = ['No.', 'Radius (R)', 'Area']
        self.columntypes = [misc.MEAS_NO, misc.MEAS_L, misc.MEAS_CUST]

        self.cust_funcs = [
            lambda data, row: data[0], # No.
            lambda data, row: data[1], # Radius
            lambda data, row: math.pi * (data[1] ** 2) if len(data) > 1 else 0 # Area = pi * R^2
        ]

        # `data` is [No., Radius] after evaluation
        self.total_func_item = lambda data: math.pi * (data[1] ** 2) if len(data) > 1 else 0

        self.total_func = lambda records, user_data: sum(item.total for item in records)

        self.itemnos_mask = ['Schedule Item No.']
        self.itemnos_mapping = [None]

        self.captions_udata = []
        self.columntypes_udata = []
        self.user_data_default = []

        self.dimensions = [[10, 20, 20], [False, False, False]]

    def get_text_value(self, records, user_data, itemnos):
        total_area = self.total_func(records, user_data)
        return f"Circle Area: {total_area:.2f} (for {len(records)} items)"

    def get_item_remark(self, record_data, user_data, itemno_data):
        return f"R={record_data[1]}"
