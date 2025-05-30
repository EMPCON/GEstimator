import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from collections import OrderedDict

class AddDependencyDialog(Gtk.Dialog):
    def __init__(self, parent, current_schedule_items, successor_task_code, existing_dependencies_str=""):
        super().__init__(title="Add/Edit Dependencies for " + successor_task_code, transient_for=parent, flags=0)
        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK
        )

import re # For parsing existing dependencies string

class AddDependencyDialog(Gtk.Dialog):
    def __init__(self, parent, current_schedule_items, successor_task_code, existing_dependencies_str=""):
        super().__init__(title="Add/Edit Dependencies for " + successor_task_code, transient_for=parent, flags=0)
        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK
        )

        self.set_default_size(450, 400)
        self.set_border_width(10)
        
        self.successor_task_code = successor_task_code
        # current_schedule_items should be an OrderedDict: {code: [code, desc, unit,...]}
        # Filter out the successor task itself from potential predecessors
        self.potential_predecessors = OrderedDict()
        if current_schedule_items:
            for code, data in current_schedule_items.items():
                if code != self.successor_task_code:
                    self.potential_predecessors[code] = data
        
        self.selected_predecessors = OrderedDict() # Store as {code: {'type': 'FS', 'lag': 0}}

        # Parse existing dependencies
        if existing_dependencies_str:
            try:
                parts = existing_dependencies_str.split(',')
                for part in parts:
                    part = part.strip()
                    if not part: continue # Skip empty parts

                    lag = 0
                    dep_type = "FS" # Default
                    
                    # Regex to capture code, type, and optional lag with sign and 'd'
                    # Example: "1.1FS+2d", "1.2SS", "1.3", "1.4FS-1d"
                    # This regex assumes type is always 2 uppercase letters.
                    # Code can contain dots.
                    match = re.fullmatch(r'([0-9A-Za-z.]+)([A-Z]{2})?([+-]\d+)?d?', part)

                    if match:
                        code_part = match.group(1)
                        
                        if match.group(2): # Type is present
                            dep_type = match.group(2)
                        
                        if match.group(3): # Lag is present
                            lag = int(match.group(3))
                        
                        # Only add if the predecessor code is valid and not the successor itself
                        if code_part in self.potential_predecessors or code_part in self.current_schedule_items : # Allow if it was a valid task
                             if code_part != self.successor_task_code:
                                self.selected_predecessors[code_part] = {'type': dep_type, 'lag': lag}
                    elif part in self.potential_predecessors or part in self.current_schedule_items: # Just a code, assume FS, 0 lag
                        if part != self.successor_task_code:
                            self.selected_predecessors[part] = {'type': 'FS', 'lag': 0}

            except Exception as e:
                print(f"Error parsing existing dependencies string '{existing_dependencies_str}': {e}")


        content_area = self.get_content_area()

        grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        content_area.pack_start(grid, True, True, 0)

        # Successor Label
        successor_label = Gtk.Label(label=f"<b>Successor Task:</b> {successor_task_code}", use_markup=True, xalign=0)
        grid.attach(successor_label, 0, 0, 3, 1)

        # Predecessor Selection
        grid.attach(Gtk.Label(label="Available Tasks (Potential Predecessors):", xalign=0), 0, 1, 1, 1)
        
        self.predecessor_store = Gtk.ListStore(str, str) # Code, Description
        for code, item_data in self.potential_predecessors.items():
            # item_data[1] is description, assuming standard structure from get_item_table
            self.predecessor_store.append([code, item_data[1] if len(item_data) > 1 else ""]) 

        self.predecessor_treeview = Gtk.TreeView(model=self.predecessor_store)
        self.predecessor_treeview.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

        for i, col_title in enumerate(["Code", "Description"]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(col_title, renderer, text=i)
            self.predecessor_treeview.append_column(column)
        
        scrollable_treelist = Gtk.ScrolledWindow()
        scrollable_treelist.set_vexpand(True)
        scrollable_treelist.set_hexpand(True)
        scrollable_treelist.set_min_content_height(150)
        scrollable_treelist.add(self.predecessor_treeview)
        grid.attach(scrollable_treelist, 0, 2, 3, 1)

        # Dependency Type
        grid.attach(Gtk.Label(label="Dependency Type:", xalign=0), 0, 3, 1, 1)
        self.type_combo = Gtk.ComboBoxText()
        self.type_combo.append_text("FS (Finish to Start)")
        self.type_combo.append_text("SS (Start to Start)")
        self.type_combo.append_text("FF (Finish to Finish)")
        self.type_combo.append_text("SF (Start to Finish)")
        self.type_combo.set_active(0) # Default to FS
        grid.attach(self.type_combo, 1, 3, 1, 1)

        # Lag
        grid.attach(Gtk.Label(label="Lag (days):", xalign=0), 0, 4, 1, 1)
        self.lag_spin = Gtk.SpinButton.new_with_range(-100, 100, 1)
        self.lag_spin.set_value(0)
        grid.attach(self.lag_spin, 1, 4, 1, 1)
        
        # Button to add selected predecessor with type/lag
        add_button = Gtk.Button(label="Set Dependency")
        add_button.connect("clicked", self.on_add_dependency_clicked)
        grid.attach(add_button, 2, 3, 1, 2) # Span 2 rows

        # Display selected dependencies
        grid.attach(Gtk.Label(label="<b>Current Dependencies:</b>", use_markup=True, xalign=0), 0, 5, 3, 1)
        self.dependencies_store = Gtk.ListStore(str, str, int, str) # Code, Type, Lag, DisplayText
        self.dependencies_treeview = Gtk.TreeView(model=self.dependencies_store)
        for i, col_title in enumerate(["Predecessor", "Type", "Lag", "Formatted"]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(col_title, renderer, text=i)
            if col_title == "Formatted": # Hide the raw formatted string, it's for output
                column.set_visible(False)
            self.dependencies_treeview.append_column(column)
        
        # Populate existing dependencies
        self.refresh_dependencies_display() # Use the refresh method to initially populate

        scrollable_deps_treelist = Gtk.ScrolledWindow()
        scrollable_deps_treelist.set_vexpand(True)
        scrollable_deps_treelist.set_hexpand(True)
        scrollable_deps_treelist.set_min_content_height(100)
        scrollable_deps_treelist.add(self.dependencies_treeview)
        grid.attach(scrollable_deps_treelist, 0, 6, 2, 1) # Span 2 columns for tree
        
        remove_button = Gtk.Button(label="Remove Selected")
        remove_button.connect("clicked", self.on_remove_dependency_clicked)
        grid.attach(remove_button, 2, 6, 1, 1)


        self.show_all()

    def on_add_dependency_clicked(self, widget):
        model, paths = self.predecessor_treeview.get_selection().get_selected_rows()
        if not paths:
            return

        dep_type_full = self.type_combo.get_active_text()
        dep_type = dep_type_full.split(" ")[0] # Get "FS", "SS", etc.
        lag = int(self.lag_spin.get_value())

        for path in paths:
            iter = model.get_iter(path)
            predecessor_code = model.get_value(iter, 0)
            
            # Update or add
            self.selected_predecessors[predecessor_code] = {'type': dep_type, 'lag': lag}
        
        self.refresh_dependencies_display()
        
    def on_remove_dependency_clicked(self, widget):
        model, path = self.dependencies_treeview.get_selection().get_selected()
        if path is not None:
            iter = model.get_iter(path)
            predecessor_code = model.get_value(iter, 0)
            if predecessor_code in self.selected_predecessors:
                del self.selected_predecessors[predecessor_code]
            model.remove(iter)

    def refresh_dependencies_display(self):
        self.dependencies_store.clear()
        for code, dep_info in self.selected_predecessors.items():
            lag_text = f"{dep_info['lag']:+d}d" if dep_info['lag'] != 0 else ""
            display_text = f"{code}{dep_info['type']}{lag_text}"
            self.dependencies_store.append([code, dep_info['type'], dep_info['lag'], display_text])

    def get_formatted_dependencies_string(self):
        if not self.selected_predecessors:
            return ""
        
        dep_list = []
        # Sort by predecessor code for consistent output
        for code in sorted(self.selected_predecessors.keys()):
            dep_info = self.selected_predecessors[code]
            lag_text = f"{dep_info['lag']:+d}d" if dep_info['lag'] != 0 else ""
            dep_list.append(f"{code}{dep_info['type']}{lag_text}")
        return ", ".join(dep_list)

    def get_dependencies_list(self):
        # Returns a list of dicts, e.g., 
        # [{'predecessor_code': '1.1', 'type': 'FS', 'lag': 0}, ...]
        deps = []
        for code, info in self.selected_predecessors.items():
            deps.append({
                'predecessor_code': code,
                'type': info['type'],
                'lag': info['lag']
            })
        return deps
