import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from decimal import Decimal, InvalidOperation

from ... import misc # For human_code, if needed for default code generation
from ...data.schedule import ResourceItemModel # To create a resource model instance

class QuickAddResourceDialog(Gtk.Dialog):
    def __init__(self, parent_window, database):
        super().__init__(title="Quick Add Resource", transient_for=parent_window, flags=0)
        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK
        )
        self.set_default_size(350, 300)
        self.set_border_width(10)

        self.database = database

        content_area = self.get_content_area()
        grid = Gtk.Grid(column_spacing=10, row_spacing=10, margin=5)
        content_area.pack_start(grid, True, True, 0)

        # Code
        lbl_code = Gtk.Label(label="Code:", xalign=0)
        self.txt_code = Gtk.Entry()
        # Suggest a new code
        self.txt_code.set_text(self.database.get_new_resource_code())
        grid.attach(lbl_code, 0, 0, 1, 1)
        grid.attach(self.txt_code, 1, 0, 1, 1)

        # Description
        lbl_desc = Gtk.Label(label="Description:", xalign=0)
        self.txt_desc = Gtk.Entry()
        grid.attach(lbl_desc, 0, 1, 1, 1)
        grid.attach(self.txt_desc, 1, 1, 1, 1)

        # Unit
        lbl_unit = Gtk.Label(label="Unit:", xalign=0)
        self.txt_unit = Gtk.Entry()
        grid.attach(lbl_unit, 0, 2, 1, 1)
        grid.attach(self.txt_unit, 1, 2, 1, 1)

        # Rate
        lbl_rate = Gtk.Label(label="Rate:", xalign=0)
        self.spin_rate = Gtk.SpinButton.new_with_range(0, 10000000, 0.01)
        self.spin_rate.set_digits(2)
        self.spin_rate.set_numeric(True)
        grid.attach(lbl_rate, 0, 3, 1, 1)
        grid.attach(self.spin_rate, 1, 3, 1, 1)
        
        # Category
        lbl_category = Gtk.Label(label="Category:", xalign=0)
        self.combo_category = Gtk.ComboBoxText()
        self.combo_category.set_entry_text_column(0)
        categories = self.database.get_resource_categories() # Assuming this returns a list of strings
        if not categories: # Ensure there's at least a default category
            self.combo_category.append_text("UNCATEGORISED")
        else:
            for category_name in categories:
                self.combo_category.append_text(category_name)
        self.combo_category.set_active(0) # Default to the first category or "UNCATEGORISED"
        grid.attach(lbl_category, 0, 4, 1, 1)
        grid.attach(self.combo_category, 1, 4, 1, 1)

        self.show_all()

    def get_resource_data(self):
        code = self.txt_code.get_text().strip()
        description = self.txt_desc.get_text().strip()
        unit = self.txt_unit.get_text().strip()
        rate_str = self.spin_rate.get_text().replace(',', '') # Handle locale issues if any
        category = self.combo_category.get_active_text()
        if category is None and self.combo_category.get_entry().get_text(): # If new category typed
            category = self.combo_category.get_entry().get_text().strip()
        elif category is None: # Fallback if nothing selected/typed
            category = "UNCATEGORISED"


        if not all([code, description, unit, rate_str]):
            return None # Validation failed

        try:
            rate = Decimal(rate_str)
            if rate < 0: return None # Rate cannot be negative
        except InvalidOperation:
            return None # Validation failed

        # Create a ResourceItemModel instance (or dict if ScheduleDatabase.insert_resource prefers that)
        resource_model = ResourceItemModel(
            code=code,
            description=description,
            unit=unit,
            rate=rate,
            vat=Decimal(0), # Default VAT to 0
            discount=Decimal(0), # Default discount to 0
            reference="",
            category=category
        )
        return resource_model

    def validate_inputs(self):
        data = self.get_resource_data()
        if data is None:
            md = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.CANCEL,
                text="Validation Error",
            )
            md.format_secondary_text(
                "All fields (Code, Description, Unit, Rate) must be filled. Rate must be a valid number."
            )
            md.run()
            md.destroy()
            return False
        
        # Check if resource code already exists
        if self.database.get_resource(data.code) is not None:
            md = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.CANCEL,
                text="Duplicate Code",
            )
            md.format_secondary_text(
                f"A resource with code '{data.code}' already exists. Please use a different code."
            )
            md.run()
            md.destroy()
            return False
            
        return True
