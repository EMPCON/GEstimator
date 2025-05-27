#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# estimator
#
#  Copyright 2014 Manu Varkey <manuvarkey@gmail.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#

import subprocess, os, ntpath, platform, sys, logging, queue, threading, pickle, copy, hashlib
import tempfile, shutil, appdirs, importlib
from decimal import Decimal
from collections import OrderedDict
from hashlib import blake2b

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, GObject, Gio, GdkPixbuf, Poppler

# local files import
from . import undo, misc, data, view

# Get logger object
log = logging.getLogger()


class MainWindow:

    # General Methods

    def display_status(self, status_code, message):
        """Displays a formated message in Infobar

            Arguments:
                status_code: Specifies the formatting of message.
                             (Takes the values misc.ERROR,
                              misc.WARNING, misc.INFO]
                message: The message to be displayed
        """
        infobar_main = self.builder.get_object("infobar_main")
        label_infobar_main = self.builder.get_object("label_infobar_main")
        infobar_revealer = self.builder.get_object("infobar_revealer")

        if status_code == misc.ERROR:
            infobar_main.set_message_type(Gtk.MessageType.ERROR)
            label_infobar_main.set_text(message)
        elif status_code == misc.WARNING:
            infobar_main.set_message_type(Gtk.MessageType.WARNING)
            label_infobar_main.set_text(message)
        elif status_code == misc.INFO:
            infobar_main.set_message_type(Gtk.MessageType.INFO)
            label_infobar_main.set_text(message)
        else:
            log.warning('display_status - Malformed status code')
            return
        log.info('display_status - ' + message)
        infobar_revealer.set_reveal_child(True)

    def set_title(self, title):
        self.gtk_header = self.builder.get_object("gtk_header")
        self.gtk_header_progress = self.builder.get_object("gtk_header_progress")

        self.gtk_header.set_subtitle(title)
        self.gtk_header_progress.set_subtitle(title)

    def set_ana_title(self, title):
        self.gtk_header_ana = self.builder.get_object("gtk_header_ana")
        self.gtk_header_ana.set_subtitle(title)

    def run_command(self, exec_func, data=None):
        """Return progress object"""

        # Show progress page
        self.hidden_stack.set_visible_child_name('Progress')
        self.hidden_stack_header.set_visible_child_name('Progress')

        # Setup progress object
        progress_label = self.builder.get_object("progress_label")
        progress_bar = self.builder.get_object("progress_bar")
        progress = misc.ProgressWindow(parent=None,
                                       label=progress_label,
                                       progress=progress_bar)

        def callback_combined(progress, data, stack, stack_header):
            # End progress
            progress.pulse(end=True)
            # Run process

            # Handle errors
            try:
                if data:
                    exec_func(progress, data)
                else:
                    exec_func(progress)
            except Exception as e:
                log.error('run_command - callback_combined' + str(e))

            # Change page
            def show_default():
                stack.set_visible_child_name('Default')
                stack_header.set_visible_child_name('Default')

            GLib.timeout_add_seconds(1, show_default)

        # Run process in seperate thread
        que = queue.Queue()
        thread = threading.Thread(target=lambda q, arg: q.put(callback_combined(progress, data, self.hidden_stack, self.hidden_stack_header)), args=(que, 2))
        thread.daemon = True
        thread.start()

    def update(self):
        """Refreshes all displays"""
        log.info('MainWindow update called')
        self.resource_view.update_store()
        self.schedule_view.update_store()
        self.measurements_view.update_store()

    def get_instance_code(self):
        """ Return unique code per document"""
        if self.filename:
            data = bytes(self.filename, 'utf-8')
        else:
            data = bytes(str(hash(self.window)), 'utf-8')
        hasher = blake2b(data, digest_size = 2)
        return hasher.hexdigest().upper()

    # Main Window

    def on_delete_window(self, *args):
        """Callback called on pressing the close button of main window"""

        log.info('MainWindow - on_exit called')

        # Ask confirmation from user
        if self.stack.haschanged():
            message = 'You have unsaved changes which will be lost if you continue.\n Are you sure you want to exit ?'
            title = 'Confirm Exit'
            dialogWindow = Gtk.MessageDialog(self.window,
                                     Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                     Gtk.MessageType.QUESTION,
                                     Gtk.ButtonsType.YES_NO,
                                     message)
            dialogWindow.set_transient_for(self.window)
            dialogWindow.set_title(title)
            dialogWindow.set_default_response(Gtk.ResponseType.NO)
            dialogWindow.show_all()
            response = dialogWindow.run()
            dialogWindow.destroy()
            if response == Gtk.ResponseType.NO:
                # Do not propogate signal
                log.info('MainWindow - on_exit - Cancelled by user')
                return True

        log.info('MainWindow - on_exit - Exiting')
        self.sch_database.close_database()
        return False

    def on_open_project_clicked(self, button=None, filename=None):
        """Open project selected by  the user"""

        if filename:
            self.filename = os.path.abspath(filename)
        else:
            # Create a filechooserdialog to open:
            # The arguments are: title of the window, parent_window, action,
            # (buttons, response)
            if platform.system() == 'Linux':
                open_dialog = Gtk.FileChooserNative.new("Open project File", self.window,
                                                    Gtk.FileChooserAction.OPEN,
                                                    "Open", "Cancel")
            elif platform.system() == 'Windows':
                open_dialog = Gtk.FileChooserDialog("Open project File", self.window,
                                                Gtk.FileChooserAction.OPEN,
                                                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                                 Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT))
            # Remote files can be selected in the file selector
            open_dialog.set_local_only(True)
            # Dialog always on top of the textview window
            open_dialog.set_modal(True)
            # Set filters
            file_filter_1 = Gtk.FileFilter()
            file_filter_1.add_pattern("*" + misc.PROJECT_EXTENSION)
            file_filter_1.add_pattern("*" + misc.PROJECT_EXTENSION.upper())
            file_filter_1.set_name("All Project Files")
            open_dialog.add_filter(file_filter_1)
            file_filter_2 = Gtk.FileFilter()
            file_filter_2.add_pattern("*.*")
            file_filter_2.set_name("All files")
            open_dialog.add_filter(file_filter_2)
            open_dialog.set_filter(file_filter_1)

            response_id = open_dialog.run()
            # If response is "ACCEPT" (the button "Save" has been clicked)
            if response_id == Gtk.ResponseType.ACCEPT:
                # get filename and set project as active
                self.filename = open_dialog.get_filename()
                # Destroy dialog
                open_dialog.destroy()
            # If response is "CANCEL" (the button "Cancel" has been clicked)
            else:
                log.info("MainWindow - on_open_project_clicked - cancelled: FileChooserAction.OPEN")
                # Destroy dialog
                open_dialog.destroy()
                self.builder.get_object('popup_open_project').hide()
                return

        try:
            # Close existing database
            self.sch_database.close_database()
            # Copy selected file to temporary location
            shutil.copyfile(self.filename, self.filename_temp)

            # Validate database
            ret_code = self.sch_database.validate_database(self.filename_temp)

            if ret_code[0] == False:
                log.exception("MainWindow - on_open_project_clicked - " + self.filename + " - " + ret_code[1])
                self.display_status(misc.ERROR, ret_code[1])
            elif ret_code[0] == True:
                # Open database
                self.sch_database.open_database(self.filename_temp)
                self.project_active = True
                # Clear stack
                self.stack.clear()
                self.stack.savepoint()
                # Set window title
                window_title = self.filename
                self.set_title(window_title)
                # Refresh
                self.update()
                # Display message
                self.display_status(misc.INFO, 'Project opened successfully')
                # Add opened file to recent manager
                recent = Gtk.RecentManager.get_default()
                uri = misc.file_to_uri(self.filename)
                recent.add_item(uri)
        except:
            log.exception("MainWindow - on_open_project_clicked - Error opening project file - " + self.filename)
            self.display_status(misc.ERROR, "Project could not be opened: Error opening file")

        self.builder.get_object('popup_open_project').hide()

    def on_open_project_selected(self, recent):
        uri = recent.get_current_uri()
        filename = misc.uri_to_file(uri)
        self.on_open_project_clicked(None, filename)
        window_title = self.filename
        self.set_title(window_title)
        self.builder.get_object('popup_open_project').hide()

    def on_save_project_clicked(self, button):
        """Save project to file already opened"""
        if self.project_active is False:
            self.on_saveas_project_clicked(button)
        else:
            try:
                # Copy current temporary file to filename
                shutil.copyfile(self.filename_temp, self.filename)
                self.display_status(misc.INFO, "Project successfully saved")
                log.info('MainWindow - on_save_project_clicked -  Project successfully saved')
                # Save point in stack for checking change state
                self.stack.savepoint()
            except:
                log.error("MainWindow - on_save_project_clicked - Error opening file - " + self.filename)
                self.display_status(misc.ERROR, "Project file could not be opened for saving")

    def on_saveas_project_clicked(self, button):
        """Save project to file selected by the user"""
        # Create a filechooserdialog to open:
        # The arguments are: title of the window, parent_window, action,
        # (buttons, response)
        if platform.system() == 'Linux':
            open_dialog = Gtk.FileChooserNative.new("Save project as...", self.window,
                                            Gtk.FileChooserAction.SAVE,
                                            "Save", "Cancel")
        elif platform.system() == 'Windows':
            open_dialog = Gtk.FileChooserDialog("Save project as...", self.window,
                                            Gtk.FileChooserAction.SAVE,
                                            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                             Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT))
        # Remote files can be selected in the file selector
        open_dialog.set_local_only(False)
        # Dialog always on top of the textview window
        open_dialog.set_modal(True)
        # Set filters
        file_filter_1 = Gtk.FileFilter()
        file_filter_1.add_pattern("*" + misc.PROJECT_EXTENSION)
        file_filter_1.add_pattern("*" + misc.PROJECT_EXTENSION.upper())
        file_filter_1.set_name("All Project Files")
        open_dialog.add_filter(file_filter_1)
        open_dialog.set_filter(file_filter_1)
        open_dialog.set_do_overwrite_confirmation(True)
        # Set default name
        open_dialog.set_current_name("newproject" + misc.PROJECT_EXTENSION)
        response_id = open_dialog.run()
        # If response is "ACCEPT" (the button "Save" has been clicked)
        if response_id == Gtk.ResponseType.ACCEPT:
            # Get filename and set project as active
            self.filename = open_dialog.get_filename()

            # Disabled as not supporting sandboxing
            # if misc.PROJECT_EXTENSION not in filename.lower():
            #     self.filename = misc.posix_path(filename + misc.PROJECT_EXTENSION)
            # else:
            #     self.filename = misc.posix_path(filename)

            self.project_active = True
            log.info('MainWindow - on_saveas_project_clicked -  Project set as active')
            # Call save project
            self.on_save_project_clicked(button)
            # Setup window name
            window_title = self.filename
            self.set_title(window_title)
            # Save point in stack for checking change state
            self.stack.savepoint()
            # Add saved file to recent manager
            recent = Gtk.RecentManager.get_default()
            uri = misc.file_to_uri(self.filename)
            recent.add_item(uri)

        # If response is "CANCEL" (the button "Cancel" has been clicked)
        elif response_id == Gtk.ResponseType.CANCEL:
            log.info("MainWindow - on_saveas_project_clicked - cancelled: FileChooserAction.OPEN")
        # Destroy dialog
        open_dialog.destroy()

    def on_project_settings_clicked(self, button):
        """Display dialog to input project settings"""
        log.info('onProjectSettingsClicked - Launch project settings')
        # Handle project settings window
        view.project.ProjectSettings(self.window, self.sch_database)

    def on_program_settings_clicked(self, button):
        """Display dialog to input project settings"""
        log.info('onProjectSettingsClicked - Launch project settings')
        # Handle project settings window
        view.project.ProgramSettings(self.window,
                                     self.sch_database,
                                     self.program_settings,
                                     self.user_library_dir)
        with open(self.settings_filename, 'wb') as fp:
            pickle.dump(self.program_settings, fp)

    def on_export_project_clicked(self, widget):
        """Export project to spreadsheet"""

        def exec_func(progress, filename):
            # Create new spreadsheet
            spreadsheet = misc.Spreadsheet()
            # Export schedule
            progress.add_message('Exporting Schedule Items...')
            progress.set_fraction(0)
            if 'export_break_items' in self.program_settings:
                break_lines = bool(eval(self.program_settings['export_break_items']))
            else:
                break_lines = False
            self.sch_database.export_sch_spreadsheet(spreadsheet, break_lines)
            # Export Resources
            progress.add_message('Exporting Resource Items...')
            progress.set_fraction(0.1)
            self.sch_database.export_res_spreadsheet(spreadsheet)
            # Export Measurements
            progress.add_message('Exporting Resource Items...')
            progress.set_fraction(0.2)
            self.sch_database.export_meas_spreadsheet(spreadsheet, break_lines)
            # Export Resource usage
            progress.add_message('Exporting Resource Usage...')
            progress.set_fraction(0.3)
            self.sch_database.export_res_usage_spreadsheet(spreadsheet)
            # Export analysis of rates
            progress.add_message('Exporting Analysis of Rates...')
            progress.set_fraction(0.4)
            self.sch_database.export_ana_spreadsheet(spreadsheet, progress, [0.3,0.9])
            # Save spreadsheet
            progress.add_message('Saving spreadsheet...')
            progress.set_fraction(0.9)
            spreadsheet.save(filename)
            progress.set_fraction(1)
            progress.add_message('<b>Export Successful</b>')
            progress.pulse(end=True)

        # Setup file save dialog
        if platform.system() == 'Linux':
            dialog = Gtk.FileChooserNative.new("Save spreadsheet as...", self.window,
                                               Gtk.FileChooserAction.SAVE, "Save", "Cancel")
        elif platform.system() == 'Windows':
            dialog = Gtk.FileChooserDialog("Save spreadsheet as...", self.window,
                                           Gtk.FileChooserAction.SAVE,
                                           (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                            Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT))
        file_filter = Gtk.FileFilter()
        file_filter.add_pattern("*.xlsx")
        file_filter.add_pattern("*.XLSX")
        file_filter.set_name("All Spreadsheet Files")

        # Set directory from project filename (Not supported by sandbox)
        if platform.system() == 'Windows':
            if self.filename:
                directory = misc.dir_from_path(self.filename)
                if directory:
                    dialog.set_current_folder(directory)

        dialog.set_current_name('BOQ.xlsx')
        dialog.add_filter(file_filter)
        dialog.set_filter(file_filter)
        dialog.set_do_overwrite_confirmation(True)

        # Run dialog and evaluate code
        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            filename = dialog.get_filename()
            dialog.destroy()
            # Setup progress dialog
            self.run_command(exec_func, filename)
            self.display_status(misc.INFO, "Project exported to spreadsheet")
            log.info('MainWindow - on_export_project_clicked - File saved as - ' + filename)
        elif response == Gtk.ResponseType.CANCEL:
            dialog.destroy()
            self.display_status(misc.WARNING, "Project export cancelled by user")
            log.info('MainWindow - on_export_project_clicked - Cancelled')

    def on_infobar_close(self, widget, response=0):
        """Hides the infobar"""
        infobar_revealer = self.builder.get_object("infobar_revealer")
        infobar_revealer.set_reveal_child(False)

    def on_redo_clicked(self, button):
        """Redo action from stack"""
        if self.stack.canredo():
            log.info(self.stack.redotext())
            self.display_status(misc.INFO, self.stack.redotext())
            self.stack.redo()
            self.update()
        else:
            self.display_status(misc.INFO, "Nothing left to Redo")

    def on_undo_clicked(self, button):
        """Undo action from stack"""
        if self.stack.canundo():
            log.info(self.stack.undotext())
            self.display_status(misc.INFO, self.stack.undotext())
            self.stack.undo()
            self.update()
        else:
            self.display_status(misc.INFO, "Nothing left to Undo")

    def on_reorder_key_pressed(self, button):
        """Undo action from stack [Ctrl]+[Shift]+[R]"""
        self.sch_database.reorder_items()
        self.display_status(misc.INFO, "Database items reordered")

    # Schedule signal handler methods

    def on_sch_add_clicked(self, button):
        """Add empty row to schedule view"""
        retval = self.sch_dialog.run()
        if retval:
            items, sub_ana_items = retval
            if items:
                ret = self.schedule_view.add_item_at_selection(items)
                ret2 = None
                if sub_ana_items:
                    ret2 = self.schedule_view.add_sub_ana_items(sub_ana_items)
                if (ret and ret[1]) or (ret2 and ret2[1]):
                    # Refresh resource view to update any items that may be added
                    self.resource_view.update_store()

    def on_sch_add_item_clicked(self, button):
        """Add empty row to schedule view"""
        item = data.schedule.ScheduleItemModel(code = '1.1',
                                              description = '',
                                              unit = '',
                                              rate = 0,
                                              qty = 0,
                                              remarks = '',
                                              ana_remarks = '',
                                              category = None,
                                              parent = None)
        self.schedule_view.add_item_at_selection([item])

    def on_sch_add_sub_item_clicked(self, button):
        """Add empty row to schedule view"""
        item = data.schedule.item = data.schedule.ScheduleItemModel(code = '1.1',
                                              description = '',
                                              unit = 'Unit',
                                              rate = 0,
                                              qty = 0,
                                              remarks = '',
                                              ana_remarks = '',
                                              category = None,
                                              parent = 'UNSET')
        self.schedule_view.add_item_at_selection([item])

    def on_sch_add_category_clicked(self, button):
        """Add empty row to schedule view"""
        newcat = self.sch_database.get_new_schedule_category_name()
        paths = self.schedule_view.add_category_at_selection(newcat)

    def on_sch_edit_clicked(self, button):
        """Edit analysis"""
        codes = self.schedule_view.get_selected_codes()
        if codes:
            code = codes[0]
            model = self.sch_database.get_item(code, modify_res_code=False)
            if model.unit != '':
                self.set_ana_title('Analysis of rates for item number ' + code)
                dialog_ana = self.analysis_view.init(model)
                # Show stack page
                self.hidden_stack.set_visible_child_name('Analysis')
                self.hidden_stack_header.set_visible_child_name('Analysis')
                self.analysis_view.tree.grab_focus()
                return
        self.display_status(misc.WARNING, "No valid item selected for editing")

    def on_sch_mark_clicked(self, button):
        """Add empty row to schedule view"""
        [item_count, with_mismatch, d1, d2, d3, without_analysis] = self.schedule_view.update_store(mark=True)
        message = "Items with rates differing from anaysis rates marked. \nTotal: {},  Mismatch: {} [Δ~0.1:🟡, Δ~1:🟠, Δ>1:🟤] ({}, {}, {}),  Missing: [🔴] {}". format(item_count, with_mismatch, d1, d2, d3, without_analysis)
        self.display_status(misc.INFO, message)

    def on_sch_colour_clicked(self, button):
        """Mark selection of schedule view with colour"""

        sch_select_colour = self.builder.get_object("sch_select_colour")
        colour_obj = sch_select_colour.get_rgba()
        colour = '#%02X%02X%02X' % (int(colour_obj.red*255), int(colour_obj.green*255), int(colour_obj.blue*255))

        self.schedule_view.update_colour(colour)

    def on_sch_reset_colour_clicked(self, button):
        """Reset color of selection in schedule view"""
        self.schedule_view.update_colour(None)

    def on_sch_refresh_clicked(self, button):
        ret_code = self.schedule_view.update_selected_rates()
        if ret_code:
            self.resource_view.update_store()
            self.display_status(misc.INFO, "Schedule rates updated from analysis")
        elif ret_code is None:
            self.display_status(misc.WARNING, "No valid items in selection")
        else:
            self.display_status(misc.ERROR, "An error occured while updating rates")

    def on_sch_refresh_meas_clicked(self, button):

        # Setup dialog window
        dialog_window = Gtk.Dialog("Select quantity rounding method", self.window, Gtk.DialogFlags.MODAL,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OK, Gtk.ResponseType.OK))
        dialog_window.set_border_width(5)
        dialog_window.get_content_area().set_spacing(15)
        dialog_window.set_size_request(400,-1)
        dialog_window.set_default_response(Gtk.ResponseType.OK)

        # Setup Data model
        rounding_values = ("Round within 1%",
                           "Round within 5%",
                           "Round within 10%",
                           "Round to 10000",
                           "Round to 1000",
                           "Round to 100",
                           "Round to 10",
                           "Round to 0",
                           "Round to .0",
                           "Round to .00",
                           "Round to .000")

        # Pack Dialog
        dialog_box = dialog_window.get_content_area()
        box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
        dialog_box.add(box)
        rounding_combo = Gtk.ComboBoxText()
        for value in rounding_values:
            rounding_combo.append_text(value)
        box.pack_start(rounding_combo, True, True, 3)
        rounding_combo.set_active(7)

        # Run dialog
        dialog_window.show_all()
        response = dialog_window.run()
        if response == Gtk.ResponseType.OK:
            # Update quantity
            selected = rounding_combo.get_active_text()
            ret_code = self.schedule_view.update_selected_qty(rounding=selected)
            if ret_code:
                self.display_status(misc.INFO, "Schedule quantiy updated from details of measurement")
            elif ret_code is None:
                self.display_status(misc.WARNING, "No valid items in selection")
            else:
                self.display_status(misc.ERROR, "An error occured while updating quantity")

        # Destroy dialog
        dialog_window.destroy()

    def on_sch_renumber_clicked(self, button):
        self.sch_database.assign_auto_item_numbers()
        self.schedule_view.update_store()
        self.display_status(misc.INFO, "Schedule items re-numbered")

    def on_sch_res_usage_clicked(self, button):
        view.resource.ResourceUsageDialog(self.window, self.sch_database).run()

    def on_schedule_delete_clicked(self, button):
        """Delete selected rows from schedule view"""
        self.schedule_view.delete_selected_items()
        log.info('MainWindow - on_schedule_delete_clicked - Selected items deleted')

    def on_copy_schedule(self, button):
        """Copy selected rows from schedule view to clipboard"""
        self.schedule_view.copy_selection()

    def on_paste_schedule(self, button):
        """Paste rows from clipboard into schedule view"""
        self.schedule_view.paste_at_selection()
        self.resource_view.update_store()

    def on_import_res_clicked(self, button):
        """Imports resources from spreadsheet selected by 'filechooserbutton_res' into resource view"""
        filename = self.builder.get_object("filechooserbutton_res").get_filename()

        columntypes = [str, str, str, float, float, float, str, str]
        captions = ['Code.', 'Description', 'Unit', 'Rate', 'VAT', 'Discount',
                    'Remarks', 'Category']
        widths = [80,200,80,80,80,80,100,100]
        expandables = [False,True,False,False,False,False,False,False]

        spreadsheet_dialog = misc.SpreadsheetDialog(self.window, filename, columntypes, captions, [widths, expandables])
        models = spreadsheet_dialog.run()

        if models:
            items = []
            resources = []
            for index, model in enumerate(models):
                if model[0] != '' and model[1] != '' and model[2] != '':
                    reference = model[6] if model[6] != '' else None
                    category = model[7] if model[7] != '' else None
                    try:
                        rate = Decimal(model[3])
                        vat = Decimal(model[4])
                        discount = Decimal(model[5])
                        res = data.schedule.ResourceItemModel(code = model[0],
                                            description = model[1],
                                            unit = model[2],
                                            rate = rate,
                                            vat = vat,
                                            discount = discount,
                                            reference = reference,
                                            category = category)
                        resources.append(res)
                    except:
                        log.warning('MainWindow - on_import_res_clicked - Error in data' + str(index))
            self.sch_database.insert_resource_multiple(resources, preserve_structure=True)
            self.display_status(misc.INFO, str(index)+' records processed')
            log.info('MainWindow - on_import_res_clicked - data added - ' + str(index) + ' records')

            self.update()
            self.display_status(misc.INFO, str(index) + " resource items inserted")
        else:
            log.info('MainWindow - on_import_res_clicked - cancelled')

    def on_update_res_clicked(self, button, column=3):
        """Updates resource from spreadsheet selected by 'filechooserbutton_res' into resource view"""
        filename = self.builder.get_object("filechooserbutton_res").get_filename()

        columntypes = [str, str, str, float, float, float, str, str]
        captions = ['Code.', 'Description', 'Unit', 'Rate', 'VAT', 'Discount',
                    'Remarks', 'Category']
        widths = [80,200,80,80,80,80,100,100]
        expandables = [False,True,False,False,False,False,False,False]

        spreadsheet_dialog = misc.SpreadsheetDialog(self.window, filename, columntypes, captions, [widths, expandables])
        models = spreadsheet_dialog.run()

        if models:
            update_dict = dict()
            for index, model in enumerate(models):
                if model[0] != '' and model[column] != '':
                    code = model[0].strip()
                    if column in (3,4,5):
                        value = Decimal(model[column])
                        update_dict[code] = value
                    elif column in (6,):
                        value = model[column]
                        update_dict[code] = value
            updated, notfound = self.sch_database.update_resource_multiple(update_dict, column)
            self.display_status(misc.INFO, str(index)+' records updated')
            log.info('MainWindow - on_update_res_clicked - data updated - ' + str(updated) + ' items | Not found - ' + str(notfound) + ' items')
            self.update()
            self.display_status(misc.INFO, str(updated) + " resource items updated, " + str(notfound) + ' items not found in resource schedule')
        else:
            log.info('MainWindow - on_update_res_clicked - cancelled')

    def on_update_sch_clicked_tax(self, button):
        self.on_update_res_clicked(button, column=4)

    def on_update_sch_clicked_discount(self, button):
        self.on_update_res_clicked(button, column=5)

    def on_update_sch_clicked_remarks(self, button):
        self.on_update_res_clicked(button, column=6)

    def on_import_sch_clicked(self, button):
        """Imports schedule from spreadsheet selected by 'filechooserbutton_schedule' into schedule view"""
        filename = self.builder.get_object("filechooserbutton_schedule").get_filename()

        columntypes = [str, str, str, float, float, float, str]
        captions = ['Code.', 'Description', 'Unit', 'Rate', 'Qty', 'Amount',
                    'Remarks']
        widths = [80, 200, 80, 80, 80, 80, 100]
        expandables = [False, True, False, False, False, False, False]

        spreadsheet_dialog = misc.SpreadsheetDialog(self.window, filename, columntypes, captions, [widths, expandables])
        models = spreadsheet_dialog.run()

        def is_child(codes, child):
            if len(codes) == 0:
                return True
            elif len(codes) > 0:
                parent_list = codes[-1].split('.')
                child_list = child.split('.')
                if len(child_list) > 1 and child_list[:-1] == parent_list:
                    return True
            return False

        def accumulate(models, index):
            desc = models[index][1]
            # If multiline item
            if models[index][2] == '':
                i = index + 1
                while (i < len(models)
                        and ((models[i][0] == '' and models[i][2] == '')
                              or (models[i][0] == '' and models[i][2] != ''))
                        and models[i][1].upper() != models[i][1]):
                    desc = desc + '\n' + models[i][1]
                    i = i + 1
                return desc, i-1
            # If single line item
            else:
                return desc, index

        category = None
        codes = []
        descs = []
        parent = None
        items = []

        if models:
            index = 1
            while index < len(models):
                model = models[index]

                # If category
                if model[1] != '' and model[2] == '' and model[1].upper() == model[1]:
                    category = model[1]

                    codes.clear()
                    descs.clear()
                    parent = None

                # If item with code
                elif model[0] != '' and model[1] != '':
                    code = model[0].strip()
                    desc, index = accumulate(models, index)

                    # If item/sub item changed
                    if not is_child(codes, code):
                        codes.pop()
                        descs.pop()
                        parent = None

                    # If blank item
                    if  models[index][2] == '' and is_child(codes, code):
                        codes.append(code)
                        descs.append(desc)
                        parent = None

                    # If final item
                    elif models[index][2] != '' and is_child(codes, code):
                        if parent is None and len(codes) > 0:
                            # Add parent item
                            sch = data.schedule.ScheduleItemModel(code = codes[-1],
                                                          description = '\n'.join(descs),
                                                          unit = '',
                                                          rate = 0,
                                                          qty = 0,
                                                          remarks = '',
                                                          category = category,
                                                          parent = None)
                            parent = codes[-1]
                            items.append(sch)

                        # Add item
                        sch = data.schedule.ScheduleItemModel(code = code,
                                                          description = desc,
                                                          unit = models[index][2],
                                                          rate = Decimal(models[index][3]),
                                                          qty = Decimal(models[index][4]),
                                                          remarks = models[index][6],
                                                          category = category,
                                                          parent = parent)
                        items.append(sch)

                    # If error item
                    else:
                        codes.clear()
                        descs.clear()
                        parent = None

                        sch = data.schedule.ScheduleItemModel(code = code,
                                                          description = desc,
                                                          unit = models[index][2],
                                                          rate = Decimal(models[index][3]),
                                                          qty = Decimal(models[index][4]),
                                                          remarks = models[index][6],
                                                          category = category,
                                                          parent = None)
                        items.append(sch)

                index = index + 1

            self.sch_database.insert_item_multiple(items, preserve_structure=True)
            self.display_status(misc.INFO, str(index)+' records processed')
            log.info('MainWindow - on_import_sch_clicked - data added - ' + str(index) + ' records')
            self.update()
            self.display_status(misc.INFO, str(index) + " schedule items inserted")
        else:
            log.info('MainWindow - on_import_sch_clicked - cancelled')

    def on_update_sch_clicked(self, button, column=3):
        """Updates schedule from spreadsheet selected by 'filechooserbutton_schedule' into schedule view"""
        filename = self.builder.get_object("filechooserbutton_schedule").get_filename()

        columntypes = [str, str, str, float, float, float, str]
        captions = ['Code.', 'Description', 'Unit', 'Rate', 'Qty', 'Amount',
                    'Remarks']
        widths = [80, 200, 80, 80, 80, 80, 100]
        expandables = [False, True, False, False, False, False, False]

        spreadsheet_dialog = misc.SpreadsheetDialog(self.window, filename, columntypes, captions, [widths, expandables])
        models = spreadsheet_dialog.run()

        if models:
            update_dict = dict()
            for index, model in enumerate(models):
                model = models[index]
                if model[0] != '' and model[column] != '':
                    code = model[0].strip()
                    if column in (3,4):
                        value = Decimal(model[column])
                        update_dict[code] = value
                index = index + 1
            updated, notfound = self.sch_database.update_item_schedule_multiple(update_dict, column)
            self.display_status(misc.INFO, str(index)+' records updated')
            log.info('MainWindow - on_update_sch_clicked - data updated - ' + str(updated) + ' items | Not found - ' + str(notfound) + ' items')
            self.update()
            self.display_status(misc.INFO, str(updated) + " schedule items updated, " + str(notfound) + ' items not found in schedule')
        else:
            log.info('MainWindow - on_import_sch_clicked - cancelled')

    def on_update_sch_clicked_qty(self, button):
        self.on_update_sch_clicked(button, column=4)

    def on_import_ana_clicked(self, button):
        """Imports analysis from spreadsheet selected by 'filechooserbutton_schedule' and links it into schedule view"""
        filename = self.builder.get_object("filechooserbutton_schedule").get_filename()

        columntypes = [str, str, str, float, float, float]
        captions = ['Code.', 'Description', 'Unit', 'Rate', 'Qty', 'Amount']
        widths = [80, 200, 80, 80, 80, 80]
        expandables = [False, True, False, False, False, False]

        # Setup spreadsheet dialog
        spreadsheet_dialog = misc.SpreadsheetDialog(self.window, filename, columntypes, captions, [widths, expandables])
        models = spreadsheet_dialog.run()

        if models:
            # Get settings from user
            ana_settings = view.analysissettings.get_analysis_settings(self.window)

            if ana_settings:

                # Import Analysis in external thread
                def exec_func(progress, models):
                    index = 0

                    while index < len(models):
                        item = data.schedule.ScheduleItemModel(None,None)
                        index = data.schedule.parse_analysis(models, item, index, True, ana_settings)
                        # Get item with corresponding code from database
                        sch_item = self.sch_database.get_item(item.code, modify_res_code=False)
                        if sch_item:
                            # Copy values to imported item
                            item.description = sch_item.description
                            item.unit = sch_item.unit
                            item.rate = sch_item.rate
                            item.qty = sch_item.qty
                            item.category = sch_item.category
                            item.remarks = sch_item.remarks
                            item.parent = sch_item.parent
                            # Update item in database
                            self.sch_database.update_item_atomic(item)
                            progress.add_message('Analysis for Item No.' + item.code + ' imported')
                            log.info('MainWindow - on_import_ana_clicked - analysis added - ' + str(item.code))
                        else:
                            progress.add_message("<span foreground='#FF0000'>Item No." + str(item.code) + ' not found in schedule items</span>')
                            log.warning('MainWindow - on_import_ana_clicked - analysis not added - code not found - ' + str(item.code))
                        # Update fraction
                        progress.set_fraction(index/len(models))

                    # Clear undo stack
                    self.stack.clear()
                    GLib.idle_add(self.resource_view.update_store)

                self.run_command(exec_func, models)


    # Analysis signal handler methods

    def on_ana_undo(self, widget):
        """Undo action from stack"""
        self.analysis_view.on_undo()

    def on_ana_redo(self, widget):
        """Redo action from stack"""
        self.analysis_view.on_redo()

    def on_ana_copy(self, widget):
        """Copy selected row to clipboard"""
        self.analysis_view.on_copy()

    def on_ana_paste(self, widget):
        """Paste copied item at selected row"""
        self.analysis_view.on_paste()

    def ana_add_res_library(self, widget):
        self.analysis_view.add_res_library(self.res_select_dialog)

    def ana_add_res(self, widget):
        self.analysis_view.add_res()

    def ana_edit_res(self, widget):
        self.analysis_view.edit_res()

    def ana_add_res_group(self, widget):
        self.analysis_view.add_res_group()

    def ana_add_sum(self, widget):
        self.analysis_view.add_sum()

    def ana_add_weight(self, widget):
       self.analysis_view.add_weight()

    def ana_add_times(self, widget):
        self.analysis_view.add_times()

    def ana_add_round(self, widget):
        self.analysis_view.add_round()

    def ana_delete_selected_row(self, widget):
        """Delete selected rows"""
        self.analysis_view.delete_selected_row()

    def on_import_clicked(self, button):
        """Imports analysis from selected spreadsheet into analysis view"""
        filename = self.builder.get_object("filechooserbutton_ana").get_filename()
        self.analysis_view.on_import_clicked(filename)

    def on_ana_save(self, button):
        # Show stack default page
        self.hidden_stack.set_visible_child_name('Default')
        self.hidden_stack_header.set_visible_child_name('Default')
        # Clean exit from analysis view
        (model_ret, res_needs_refresh) = self.analysis_view.exit()
        # Update item
        self.sch_database.update_item(model_ret)
        # Refresh resource view to update any items that may be added
        if res_needs_refresh:
            self.resource_view.update_store()

    def on_ana_cancel(self, button):
        # Show stack default page
        self.hidden_stack.set_visible_child_name('Default')
        self.hidden_stack_header.set_visible_child_name('Default')
        # Clean exit from analysis view
        self.analysis_view.exit()
        # Refresh resource view to update any items that may be added
        if self.analysis_view.res_needs_refresh:
            self.resource_view.update_store()


    # Measurement signal handler methods

    def on_meas_heading_menu_clicked(self, button):
        """Add a Heading object to measurement view"""
        code = self.measurements_view.add_heading()
        if code is not None:
            self.display_status(*code)

    def on_meas_custom_menu_clicked(self, button, module):
        """Callback function for click event of custom measurement item"""
        code = self.measurements_view.add_custom(None,module)
        if code is not None:
            self.display_status(*code)

    def on_meas_delete_clicked(self, button):
        """Delete selected item from measurement view"""
        self.measurements_view.delete_selected_row()

    def on_meas_clicked(self, button, event):
        """Edit measurement view object on double click"""
        if event.type == Gdk.EventType._2BUTTON_PRESS:
            self.measurements_view.edit_selected_row()

    def on_meas_edit_clicked(self, button):
        """Edit selected item in measurement view"""
        self.measurements_view.edit_selected_row()

    def on_meas_properties_clicked(self, button):
        """Edit properties of supported items in measurement view"""
        code = self.measurements_view.edit_selected_properties()
        if code is not None:
            self.display_status(*code)

    def on_meas_copy_clicked(self, button):
        """Copy selected item in measurement view to clipboard"""
        self.measurements_view.copy_selection()

    def on_meas_paste_clicked(self, button):
        """Paste item from clipboard to measurement view"""
        self.measurements_view.paste_at_selection()

    # Digital Takeoffs signal handler methods
    def on_load_pdf_takeoffs_clicked(self, widget):
        """Load a PDF file for digital takeoffs."""
        dialog = Gtk.FileChooserDialog(
            title="Please choose a PDF file",
            parent=self.window,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )

        file_filter_pdf = Gtk.FileFilter()
        file_filter_pdf.set_name("PDF files")
        file_filter_pdf.add_mime_type("application/pdf")
        dialog.add_filter(file_filter_pdf)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            pdf_path = dialog.get_filename()
            try:
                pdf_uri = GLib.filename_to_uri(pdf_path, None)
                poppler_doc = Poppler.Document.new_from_file(pdf_uri, None)
                if poppler_doc and poppler_doc.get_n_pages() > 0:
                    self.poppler_doc = poppler_doc
                    self.poppler_page = self.poppler_doc.get_page(0) # Store first page
                    
                    page_width_pdf, page_height_pdf = self.poppler_page.get_size()
                    
                    scrolled_window = self.builder.get_object("scrolledwindow_pdf_takeoffs")
                    alloc = scrolled_window.get_allocation()
                    available_width = alloc.width if alloc.width > 1 else 600 
                    available_height = alloc.height if alloc.height > 1 else 800
                    
                    available_width -= 2  # Account for border/padding
                    available_height -= 2

                    scale_w = available_width / page_width_pdf if page_width_pdf > 0 else 1.0
                    scale_h = available_height / page_height_pdf if page_height_pdf > 0 else 1.0
                    self.pdf_render_scale = min(scale_w, scale_h, 1.0) 

                    render_width = int(page_width_pdf * self.pdf_render_scale)
                    render_height = int(page_height_pdf * self.pdf_render_scale)
                    
                    # Connect size-allocate for the image if not already connected
                    if not hasattr(self, 'image_size_allocate_handler_id') or not self.image_size_allocate_handler_id:
                        self.image_size_allocate_handler_id = self.image_pdf_takeoffs.connect("size-allocate", self.on_pdf_image_size_allocate)

                    pixbuf = self.poppler_page.render_to_pixbuf(0, 0, render_width, render_height, self.pdf_render_scale, 0)
                    self.image_pdf_takeoffs.set_from_pixbuf(pixbuf)
                    # Call explicitly after setting pixbuf, as size-allocate might not trigger if size is same
                    self.on_pdf_image_size_allocate(self.image_pdf_takeoffs, self.image_pdf_takeoffs.get_allocation())


                    self.takeoff_shapes = [] 
                    self.drawing_area_takeoffs.queue_draw()
                    self.display_status(misc.INFO, f"Loaded PDF: {os.path.basename(pdf_path)}")
                else:
                    self.poppler_doc = None
                    self.poppler_page = None
                    self.image_pdf_takeoffs.clear()
                    self.display_status(misc.ERROR, "Could not load PDF or PDF has no pages.")
            except GLib.Error as e:
                self.poppler_doc = None
                self.poppler_page = None
                self.image_pdf_takeoffs.clear()
                self.display_status(misc.ERROR, f"Error loading PDF: {e.message}")
                log.error(f"Error loading PDF: {e}")
        dialog.destroy()

    def on_pdf_image_size_allocate(self, widget, allocation):
        self.drawing_area_takeoffs.set_size_request(allocation.width, allocation.height)
        if self.poppler_page:
            page_width_pdf, page_height_pdf = self.poppler_page.get_size()
            render_width = int(page_width_pdf * self.pdf_render_scale)
            render_height = int(page_height_pdf * self.pdf_render_scale)
            self.pdf_render_offset_x = max(0, (allocation.width - render_width) / 2)
            self.pdf_render_offset_y = max(0, (allocation.height - render_height) / 2)
        self.drawing_area_takeoffs.queue_draw()


    def on_tool_draw_line_selected(self, widget):
        self.current_draw_tool = "line"
        self.display_status(misc.INFO, "Line tool selected. Click and drag on the PDF to draw.")

    def on_tool_draw_rectangle_selected(self, widget):
        self.current_draw_tool = "rectangle"
        self.display_status(misc.INFO, "Rectangle tool selected. Click and drag on the PDF to draw.")

    def _view_to_pdf_coords(self, view_x, view_y):
        if not self.poppler_page or self.pdf_render_scale == 0:
            return None
        x_on_rendered_pdf = view_x - self.pdf_render_offset_x
        y_on_rendered_pdf = view_y - self.pdf_render_offset_y
        pdf_x = x_on_rendered_pdf / self.pdf_render_scale
        pdf_y = y_on_rendered_pdf / self.pdf_render_scale
        return pdf_x, pdf_y

    def _pdf_to_view_coords(self, pdf_x, pdf_y):
        if not self.poppler_page:
            return None
        x_on_rendered_pdf = pdf_x * self.pdf_render_scale
        y_on_rendered_pdf = pdf_y * self.pdf_render_scale
        view_x = x_on_rendered_pdf + self.pdf_render_offset_x
        view_y = y_on_rendered_pdf + self.pdf_render_offset_y
        return view_x, view_y

    def on_takeoff_drawing_area_button_press(self, widget, event):
        if self.current_draw_tool and event.button == Gdk.BUTTON_PRIMARY and self.poppler_page:
            coords = self._view_to_pdf_coords(event.x, event.y)
            if coords:
                self.is_drawing = True
                self.draw_start_point = coords
                self.draw_current_point = coords 
                widget.grab_focus()


    def on_takeoff_drawing_area_motion_notify(self, widget, event):
        if self.is_drawing and self.draw_start_point and self.poppler_page:
            coords = self._view_to_pdf_coords(event.x, event.y)
            if coords:
                self.draw_current_point = coords
                widget.queue_draw() 

    def on_takeoff_drawing_area_button_release(self, widget, event):
        if self.is_drawing and self.current_draw_tool and self.draw_start_point and self.draw_current_point and event.button == Gdk.BUTTON_PRIMARY and self.poppler_page:
            start_pdf_x, start_pdf_y = self.draw_start_point
            curr_pdf_x, curr_pdf_y = self.draw_current_point

            shape_data = None
            if abs(start_pdf_x - curr_pdf_x) > 0.1 or abs(start_pdf_y - curr_pdf_y) > 0.1: 
                if self.current_draw_tool == "line":
                    shape_data = {'type': "line", 'page_index': self.poppler_page.get_index(), 'coords': [(start_pdf_x, start_pdf_y), (curr_pdf_x, curr_pdf_y)]}
                elif self.current_draw_tool == "rectangle":
                    rect_x = min(start_pdf_x, curr_pdf_x)
                    rect_y = min(start_pdf_y, curr_pdf_y)
                    rect_w = abs(start_pdf_x - curr_pdf_x)
                    rect_h = abs(start_pdf_y - curr_pdf_y)
                    shape_data = {'type': "rectangle", 'page_index': self.poppler_page.get_index(), 'coords': [rect_x, rect_y, rect_w, rect_h]}
            
            if shape_data:
                self.takeoff_shapes.append(shape_data)
                log.info(f"Added shape: {shape_data}")
            
            self.is_drawing = False
            widget.queue_draw() 

    def on_takeoff_drawing_area_draw(self, widget, cr):
        if not self.poppler_page:
            return False 

        cr.set_line_width(2) 
        for shape in self.takeoff_shapes:
            if shape['page_index'] == self.poppler_page.get_index():
                cr.set_source_rgba(1.0, 0.0, 0.0, 0.8) 
                if shape['type'] == "line":
                    p1_pdf, p2_pdf = shape['coords']
                    p1_view = self._pdf_to_view_coords(p1_pdf[0], p1_pdf[1])
                    p2_view = self._pdf_to_view_coords(p2_pdf[0], p2_pdf[1])
                    if p1_view and p2_view:
                        cr.move_to(p1_view[0], p1_view[1])
                        cr.line_to(p2_view[0], p2_view[1])
                        cr.stroke()
                elif shape['type'] == "rectangle":
                    x_pdf, y_pdf, w_pdf, h_pdf = shape['coords']
                    top_left_view = self._pdf_to_view_coords(x_pdf, y_pdf)
                    w_view = w_pdf * self.pdf_render_scale
                    h_view = h_pdf * self.pdf_render_scale
                    if top_left_view:
                        cr.rectangle(top_left_view[0], top_left_view[1], w_view, h_view)
                        cr.stroke()
        
        if self.is_drawing and self.current_draw_tool and self.draw_start_point and self.draw_current_point:
            cr.set_source_rgba(0.0, 0.0, 1.0, 0.5) 
            p1_view = self._pdf_to_view_coords(self.draw_start_point[0], self.draw_start_point[1])
            p2_view = self._pdf_to_view_coords(self.draw_current_point[0], self.draw_current_point[1])

            if p1_view and p2_view:
                if self.current_draw_tool == "line":
                    cr.move_to(p1_view[0], p1_view[1])
                    cr.line_to(p2_view[0], p2_view[1])
                    cr.stroke()
                elif self.current_draw_tool == "rectangle":
                    rect_x_view = min(p1_view[0], p2_view[0])
                    rect_y_view = min(p1_view[1], p2_view[1])
                    rect_w_view = abs(p1_view[0] - p2_view[0])
                    rect_h_view = abs(p1_view[1] - p2_view[1])
                    cr.rectangle(rect_x_view, rect_y_view, rect_w_view, rect_h_view)
                    cr.stroke()
        return False

    def on_takeoff_drawing_area_configure_event(self, widget, event):
        if self.poppler_page: 
            self.on_pdf_image_size_allocate(self.image_pdf_takeoffs, self.image_pdf_takeoffs.get_allocation())
        widget.queue_draw()
        return True

    def on_takeoff_scroll_changed(self, adjustment):
        self.drawing_area_takeoffs.queue_draw()

    # Quoting signal handler methods
    def on_create_quote_from_estimate_clicked(self, widget):
        log.info("Populating Quote from Current Estimate")
        self.entry_quote_title.set_text(self.gtk_header.get_subtitle() or "New Quote")
        self.entry_quote_client_name.set_text("")
        self.entry_quote_client_address.set_text("")
        now = GLib.DateTime.new_now_local()
        self.entry_quote_date.set_text(now.format("%Y-%m-%d"))

        self.quote_items_store.clear()
        if self.schedule_view and self.schedule_view.tree:
            schedule_model = self.schedule_view.tree.get_model()
            if schedule_model:
                for row in schedule_model: # Iterate through Gtk.TreeModel
                    try:
                        item_no = row[self.schedule_view.COL_CODE]
                        desc = row[self.schedule_view.COL_DESCRIPTION]
                        qty = float(row[self.schedule_view.COL_QTY])
                        unit = row[self.schedule_view.COL_UNIT]
                        rate = float(row[self.schedule_view.COL_RATE])
                        amount = float(row[self.schedule_view.COL_AMOUNT])
                        self.quote_items_store.append([item_no, desc, qty, unit, rate, amount])
                    except Exception as e:
                        log.error(f"Error processing schedule row for quote: {row[:]} - {e}")
            else:
                log.warning("Schedule model not found for quoting.")
        else:
            log.warning("Schedule view or tree not found for quoting.")
        
        self.update_quote_preview(None) 

    def _get_quote_preview_text(self):
        title = self.entry_quote_title.get_text()
        client_name = self.entry_quote_client_name.get_text()
        client_address = self.entry_quote_client_address.get_text()
        quote_date = self.entry_quote_date.get_text()

        preview_text = f"QUOTE\n\n"
        preview_text += f"Title: {title}\n"
        preview_text += f"Date: {quote_date}\n\n"
        preview_text += f"Client: {client_name}\n"
        preview_text += f"Address: {client_address}\n\n"
        preview_text += f"{'-'*80}\n"
        preview_text += f"{'Item No.':<10} {'Description':<30} {'Qty':>7} {'Unit':<5} {'Rate':>10} {'Amount':>12}\n"
        preview_text += f"{'-'*80}\n"

        total_quote_amount = 0.0
        for row in self.quote_items_store:
            item_no, desc, qty, unit, rate, amount = row
            preview_text += f"{item_no:<10} {desc:<30} {qty:>7.2f} {unit:<5} {rate:>10.2f} {amount:>12.2f}\n"
            total_quote_amount += amount
        
        preview_text += f"{'-'*80}\n"
        preview_text += f"{'TOTAL:':>65} {total_quote_amount:>12.2f}\n"
        preview_text += f"{'-'*80}\n"
        return preview_text

    def update_quote_preview(self, widget=None, event=None): 
        preview_text = self._get_quote_preview_text()
        buf = self.textview_quote_preview.get_buffer()
        buf.set_text(preview_text)

    def on_generate_save_quote_clicked(self, widget):
        log.info("Generate & Save Quote button clicked.")
        quote_content = self._get_quote_preview_text()
        
        dialog = Gtk.FileChooserDialog(
            title="Save Quote As...",
            parent=self.window,
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK
        )

        default_filename = f"Quote - {self.entry_quote_title.get_text()}.txt"
        dialog.set_current_name(default_filename)

        filter_text = Gtk.FileFilter()
        filter_text.set_name("Text files")
        filter_text.add_mime_type("text/plain")
        dialog.add_filter(filter_text)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filepath = dialog.get_filename()
            if not filepath.lower().endswith(".txt"):
                filepath += ".txt"
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(quote_content)
                self.display_status(misc.INFO, f"Quote saved successfully to {filepath}")
                log.info(f"Quote saved to {filepath}")
            except Exception as e:
                self.display_status(misc.ERROR, f"Error saving quote: {e}")
                log.error(f"Error saving quote to {filepath}: {e}")
        dialog.destroy()

    # Resource signal handler methods

    def on_res_add_clicked(self, button):
        """Add empty row to schedule view"""
        res = data.schedule.ResourceItemModel(code = None,
                                            description = '',
                                            unit = '',
                                            rate = 0,
                                            vat=0,
                                            discount=0)
        self.resource_view.add_resource_at_selection([res])

    def on_res_add_category_clicked(self, button):
        """Add empty category to schedule view"""
        newcat = self.sch_database.get_new_resource_category_name()
        self.resource_view.add_category_at_selection(newcat)

    def on_res_load_rates_clicked(self, button):
        """Load resource rates from database"""
        dialog = view.resource.SelectResourceDialog(self.window,
                                self.sch_database,
                                select_database_mode=True)
        databasename = dialog.run()

        if databasename:
            self.sch_database.update_resource_from_database(databasename)
            self.resource_view.update_store()
            self.display_status(misc.INFO, "Rates updated from database")

    def on_res_renumber_clicked(self, button):
        """Renumber resource items"""
        exclude_list = []  # Libraries to be excluded from renumber

        # Setup dialog window
        dialog_window = Gtk.Dialog("Select libraries to be renumbered", self.window, Gtk.DialogFlags.MODAL,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OK, Gtk.ResponseType.OK))
        dialog_window.set_title("Select libraries to be renumbered")
        dialog_window.set_border_width(5)
        dialog_window.get_content_area().set_spacing(15)
        dialog_window.set_size_request(400,-1)
        dialog_window.set_default_response(Gtk.ResponseType.OK)

        # Pack Dialog
        dialog_box = dialog_window.get_content_area()
        box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
        dialog_box.add(box)
        check_dict = dict()
        for code in self.sch_database.get_res_library_codes():
            checkbox = Gtk.ToggleButton.new_with_label(code)
            checkbox.set_active(False)
            check_dict[code] = checkbox
            box.pack_start(checkbox, True, True, 3)

        # Run dialog
        dialog_window.show_all()
        response = dialog_window.run()
        if response == Gtk.ResponseType.OK:
            for code in check_dict:
                if check_dict[code].get_active() == False:
                    exclude_list.append(code)
            # Do renumbering
            self.sch_database.assign_auto_item_numbers_res(exclude=exclude_list)
            self.resource_view.update_store()
            self.display_status(misc.INFO, "Resource items re-numbered")

        # Destroy dialog
        dialog_window.destroy()

    def on_res_delete_clicked(self, button):
        """Delete selected rows from resource view"""
        self.resource_view.delete_selected_item()
        log.info('MainWindow - on_schedule_delete_clicked - Selected items deleted')

    def on_cut_res(self, button):
        """Cut selected rows from resource view to clipboard"""
        self.resource_view.cut_selection()

    def on_copy_res(self, button):
        """Copy selected rows from resource view to clipboard"""
        self.resource_view.copy_selection()

    def on_paste_res(self, button):
        """Paste rows from clipboard into resource view"""
        self.resource_view.paste_at_selection()

    def on_res_sync_rates_clicked(self, button):
        """Synchronise rates from schedule for subanalysis items"""
        self.resource_view.update_resource_from_schedule()


    # General signal handler methods

    def on_refresh(self, widget):
        """Refresh display of views"""
        log.info('on_refresh called')
        self.update()
        self.display_status(misc.INFO, "Project Refreshed")

    def drag_data_received(self, widget, context, x, y, selection, target_type, timestamp):
        if target_type == 80:
            data_str = selection.get_data().decode('utf-8')
            uri = data_str.strip('\r\n\x00')
            file_uri = uri.split()[0] # we may have more than one file dropped
            filename = misc.get_file_path_from_dnd_dropped_uri(file_uri)

            if os.path.isfile(filename):
                # Ask confirmation from user
                if self.stack.haschanged():
                    message = 'You have unsaved changes which will be lost if you continue.\n Are you sure you want to discard these changes ?'
                    title = 'Confirm Open'
                    dialogWindow = Gtk.MessageDialog(self.window,
                                             Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                             Gtk.MessageType.QUESTION,
                                             Gtk.ButtonsType.YES_NO,
                                             message)
                    dialogWindow.set_transient_for(self.window)
                    dialogWindow.set_title(title)
                    dialogWindow.set_default_response(Gtk.ResponseType.NO)
                    dialogWindow.show_all()
                    response = dialogWindow.run()
                    dialogWindow.destroy()
                    if response != Gtk.ResponseType.YES:
                        # Do not open file
                        log.info('MainWindow - drag_data_received - Cancelled by user')
                        return

                # Open file
                self.on_open_project_clicked(None, filename)
                log.info('MainApp - drag_data_received  - opnened file ' + filename)

    def initialise(self):
        # Open temporary file for database
        (temp_fpointer, self.filename_temp) = tempfile.mkstemp(prefix=misc.PROGRAM_NAME+'_tempproj_' +str(self.id) + '_')

        # Initialise undo/redo stack
        self.stack = undo.Stack()
        # Save point in stack for checking change state
        self.stack.savepoint()

        log.info('Setting up main Database')
        # Setup schedule database
        self.sch_database = data.schedule.ScheduleDatabase(self.stack)
        self.sch_database.create_new_database(self.filename_temp)
        log.info('Database initialised')

        log.info('Setting up program settings')
        dirs = appdirs.AppDirs(misc.PROGRAM_NAME, misc.PROGRAM_AUTHOR, version=misc.PROGRAM_VER)
        settings_dir = dirs.user_data_dir
        self.user_library_dir = misc.posix_path(dirs.user_data_dir,'database')
        self.settings_filename = misc.posix_path(settings_dir,'settings.ini')

        # Create directory if does not exist
        if not os.path.exists(settings_dir):
            os.makedirs(settings_dir)
        if not os.path.exists(self.user_library_dir):
            os.makedirs(self.user_library_dir)
        
        self.program_settings = copy.deepcopy(misc.default_program_settings)
        try:
            if os.path.exists(self.settings_filename):
                with open(self.settings_filename, 'rb') as fp:
                    program_settings = pickle.load(fp)
                    self.program_settings.update(program_settings)
                    log.info('Program settings opened at ' + str(self.settings_filename))
            else:
                self.program_settings = copy.deepcopy(misc.default_program_settings)
                with open(self.settings_filename, 'wb') as fp:
                    pickle.dump(self.program_settings, fp)
                log.info('Program settings saved at ' + str(self.settings_filename))
        except:
            log.info('Default program settings loaded')
        log.info('Program settings initialised')

        log.info('Setting up Libraries')

        # Add default path
        file_names = os.listdir(misc.abs_path('database'))
        library_names = []
        for f in file_names:
            if f[-len(misc.PROJECT_EXTENSION):].lower() == misc.PROJECT_EXTENSION:
                library_names.append(misc.abs_path('database',f))

        # Add user datapath
        file_names = os.listdir(self.user_library_dir)
        for f in file_names:
            if f[-len(misc.PROJECT_EXTENSION):].lower() == misc.PROJECT_EXTENSION:
                library_names.append(misc.posix_path(self.user_library_dir,f))

        for library_name in library_names:
            if self.sch_database.add_library(library_name):
                log.info('MainWindow - ' + library_name + ' - added')
            else:
                log.warning('MainWindow - ' + library_name + ' - not added')

        # Setup custom measurement items
        file_names = [f for f in os.listdir(misc.abs_path('meas_templates'))]
        module_names = []
        for f in file_names:
            if f[-3:] == '.py' and f != '__init__.py':
                module_names.append(f[:-3])
        self.custom_menus = []
        module_names.sort()

        popupmenu = self.builder.get_object("popover_meas_box")

        for module_name in module_names:
            try:
                spec = importlib.util.spec_from_file_location(module_name, misc.abs_path('meas_templates', module_name+'.py'))
                module = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = module
                spec.loader.exec_module(module)
                custom_object = module.CustomItem()
                name = custom_object.name
                menuitem = Gtk.ModelButton(text=name)
                popupmenu.pack_start(menuitem, False, False, 0)
                menuitem.set_visible(True)
                menuitem.connect("clicked", self.on_meas_custom_menu_clicked, module_name)
                self.custom_menus.append(menuitem)
                log.info('Plugin loaded - ' + module_name)
            except ImportError:
                log.error('Error Loading plugin - ' + module_name)

        log.info('Library initialisation complete')

        # Initialise window variables
        self.hidden_stack = self.builder.get_object("hidden_stack")
        self.hidden_stack_header = self.builder.get_object("hidden_stack_header")

        # Setup darkmode
        text_color = self.window.get_style_context().get_color(Gtk.StateFlags.NORMAL)
        back_color = self.window.get_style_context().get_background_color(Gtk.StateFlags.NORMAL)
        textavg = (text_color.red + text_color.green + text_color.blue)/3
        backavg = (back_color.red + back_color.green + back_color.blue)/3
        if textavg > backavg:  # Darkish theme
            self.darkmode = True
        else:  # Lightish theme
            self.darkmode = False

        # Setup font settings
        # Set default application font for windows
        if platform.system() == 'Windows':
            cssprovider = Gtk.CssProvider()
            cssprovider.load_from_data(str.encode("*{font-family: consolas, segoe ui; font-size:11pt}"))
            self.window.get_style_context().add_provider_for_screen(Gdk.Screen.get_default(), cssprovider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

        # Other variables
        self.filename = None

        # Initialise resource view
        box_res = self.builder.get_object("box_res")
        self.resource_view = view.resource.ResourceView(self.window, self.sch_database, box_res, instance_code_callback=self.get_instance_code)

        # Initialise schedule view
        box_sch = self.builder.get_object("box_sch")
        self.schedule_view = view.schedule.ScheduleView(self.window, self.sch_database, box_sch, show_sum=True, instance_code_callback=self.get_instance_code)

        # Initialise analysis view
        self.analysis_tree = self.builder.get_object("treeview_analysis")
        self.analysis_remark_entry = self.builder.get_object("entry_analysis_remarks")
        self.analysis_view = view.analysis.AnalysisView(self.window,
                                                        self.analysis_tree,
                                                        self.analysis_remark_entry,
                                                        self.sch_database,
                                                        self.program_settings,
                                                        instance_code_callback=self.get_instance_code)

        # Initialise measurement view
        treeview_meas = self.builder.get_object("treeview_meas")
        self.measurements_view = view.measurement.MeasurementsView(self.window, self.sch_database, treeview_meas)

        # Initialise Digital Takeoffs view elements
        self.image_pdf_takeoffs = self.builder.get_object("image_pdf_takeoffs")
        self.drawing_area_takeoffs = self.builder.get_object("drawing_area_takeoffs")
        self.overlay_pdf_takeoffs = self.builder.get_object("overlay_pdf_takeoffs")
        # Tool buttons are connected via builder.connect_signals

        self.current_draw_tool = None
        self.is_drawing = False
        self.draw_start_point = None
        self.draw_current_point = None
        self.takeoff_shapes = [] 
        self.poppler_doc = None
        self.poppler_page = None
        self.pdf_render_scale = 1.0 
        self.pdf_render_offset_x = 0 
        self.pdf_render_offset_y = 0
        self.image_size_allocate_handler_id = None # To store the handler ID

        # Connect scroll adjustments to redraw drawing area
        scrolled_window_pdf = self.builder.get_object("scrolledwindow_pdf_takeoffs")
        hadjustment = scrolled_window_pdf.get_hadjustment()
        vadjustment = scrolled_window_pdf.get_vadjustment()
        if hadjustment:
            hadjustment.connect("value-changed", self.on_takeoff_scroll_changed)
        if vadjustment:
            vadjustment.connect("value-changed", self.on_takeoff_scroll_changed)

        # Initialise Quoting view elements
        self.entry_quote_title = self.builder.get_object("entry_quote_title")
        self.entry_quote_client_name = self.builder.get_object("entry_quote_client_name")
        self.entry_quote_client_address = self.builder.get_object("entry_quote_client_address")
        self.entry_quote_date = self.builder.get_object("entry_quote_date")
        self.treeview_quote_items = self.builder.get_object("treeview_quote_items")
        self.textview_quote_preview = self.builder.get_object("textview_quote_preview")
        self.button_generate_save_quote = self.builder.get_object("button_generate_save_quote")
        self.button_generate_save_quote.connect("clicked", self.on_generate_save_quote_clicked)


        # Setup GtkListStore for treeview_quote_items
        # Columns: Item No.(str), Description(str), Quantity(float), Unit(str), Rate(float), Amount(float)
        self.quote_items_store = Gtk.ListStore(str, str, float, str, float, float)
        self.treeview_quote_items.set_model(self.quote_items_store)
        column_titles = ["Item No.", "Description", "Quantity", "Unit", "Rate", "Amount"]
        for i, title in enumerate(column_titles):
            renderer = Gtk.CellRendererText()
            if title in ["Quantity", "Rate", "Amount"]:
                renderer.set_property("xalign", 1.0) # Right align numeric columns
            column = Gtk.TreeViewColumn(title, renderer, text=i)
            self.treeview_quote_items.append_column(column)

        # Connect signals for live preview update
        self.entry_quote_title.connect("changed", self.update_quote_preview)
        self.entry_quote_client_name.connect("changed", self.update_quote_preview)
        self.entry_quote_client_address.connect("changed", self.update_quote_preview)
        self.entry_quote_date.connect("changed", self.update_quote_preview)
        self.quote_items_store.connect("row-inserted", self.update_quote_preview)
        self.quote_items_store.connect("row-deleted", self.update_quote_preview)
        self.quote_items_store.connect("row-changed", self.update_quote_preview)


        # Main stack
        self.stack_main = self.builder.get_object("stack_main")
        self.stack_sidebar = self.builder.get_object("stack_sidebar") 
        self.main_paned = self.builder.get_object("main_paned") 

        # Darg-Drop support for files
        self.window.drag_dest_set( Gtk.DestDefaults.MOTION | Gtk.DestDefaults.HIGHLIGHT | Gtk.DestDefaults.DROP,
                  [Gtk.TargetEntry.new("text/uri-list", 0, 80)],
                  Gdk.DragAction.COPY)
        self.window.connect('drag-data-received', self.drag_data_received)

        # Setup schedule dialog for selecting database items
        log.info('Setting up Dialog windows')
        self.sch_dialog = view.schedule.SelectScheduleDialog(self.window, self.sch_database, self.program_settings)
        self.res_select_dialog = view.resource.SelectResourceDialog(self.window, self.sch_database)

        if self.id == 0:
            self.splash.exit()

        self.window.show_all()
        # Set flag for other processes
        self.finished_setting_up = True
        log.info('Dialog windows initialised')

    def __init__(self, id=0):
        log.info('MainWindow - Initialising')

        # Setup main window
        self.builder = Gtk.Builder()

        self.builder.add_from_file(misc.abs_path("interface", "mainwindow.glade"))

        self.window = self.builder.get_object("window_main")
        self.builder.connect_signals(self)

        # Check for project active status
        self.project_active = False
        self.id = id

        # Set flag for other processes
        self.finished_setting_up = False

        if id == 0:
            # Start splash screen
            self.splash = misc.SplashScreen(self.initialise, misc.abs_path("interface", "splash.png"))
        else:
            self.initialise()


class MainApp(Gtk.Application):
    """Class handles application related tasks"""

    def __init__(self, *args, **kwargs):
        log.info('MainApp - Start initialisation')

        super().__init__(*args, application_id="com.kavilgroup.gestimator",
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
                         **kwargs)

        self.window = None
        self.about_dialog = None
        self.windows = []

        self.add_main_option("test", ord("t"), GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE, "Command line test", None)

        log.info('MainApp - Initialised')


    # Application function overloads

    def do_startup(self):
        log.info('MainApp - do_startup - Start')

        Gtk.Application.do_startup(self)

        action = Gio.SimpleAction.new("new", None)
        action.connect("activate", self.on_new)
        self.add_action(action)

        action = Gio.SimpleAction.new("help", None)
        action.connect("activate", self.on_help)
        self.add_action(action)

        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.on_about)
        self.add_action(action)

        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", self.on_quit)
        self.add_action(action)

        # Disable app menu since deprecated
        # builder = Gtk.Builder.new_from_string(misc.MENU_XML, -1)
        # self.set_app_menu(builder.get_object("app-menu"))

        log.info('MainApp - do_startup - End')

    def do_activate(self):
        log.info('MainApp - do_activate - Start')

        self.window = MainWindow(len(self.windows))
        self.windows.append(self.window)
        self.add_window(self.window.window)

        log.info('MainApp - do_activate - End')

    def do_open(self, files, hint):

        def call_open(window, filename):
            if window.finished_setting_up:
                log.info('MainApp - do_open - call_open - Start')
                window.on_open_project_clicked(None, filename)
                log.info('MainApp - do_open - call_open - opened file ' + filename)
                return False
            else:
                return True

        log.info('MainApp - do_open - Start')
        self.activate()
        if len(files) > 0:
            filename = files[0].get_path()
            GLib.timeout_add(500, call_open, self.window, filename)
        log.info('MainApp - do_open  - End')
        return 0

    def do_command_line(self, command_line):

        def call_open(window, filename):
            if window.finished_setting_up:
                log.info('MainApp - do_command_line - call_open - Start')
                window.on_open_project_clicked(None, filename)
                log.info('MainApp - do_command_line - call_open - opened file ' + filename)
                return False
            else:
                return True

        log.info('MainApp - do_command_line - Start')
        options = command_line.get_arguments()
        self.activate()
        if len(options) > 1:
            filename = misc.uri_to_file(options[1])
            GLib.timeout_add(500, call_open, self.window, filename)
        log.info('MainApp - do_command_line - End')
        return 0

    # Application callbacks

    def on_about(self, action, param):
        """Show about dialog"""
        log.info('MainApp - Show About window')
        # Setup about dialog
        self.builder = Gtk.Builder()
        self.builder.add_from_file(misc.abs_path("interface", "aboutdialog.glade"))
        self.about_dialog = self.builder.get_object("aboutdialog")
        self.about_dialog.set_transient_for(self.get_active_window())
        self.about_dialog.set_modal(True)
        self.about_dialog.run()
        self.about_dialog.destroy()

    def on_help(self, action, param):
        """Launch help file"""
        log.info('onHelpClick - Launch Help file')
        misc.open_file('https://manuvarkey.github.io/GEstimator/', abs=False)

    def on_new(self, action, param):
        """Launch a new instance of the application"""
        log.info('MainApp - Raise new window')
        self.do_activate()

    def on_quit(self, action, param):
        self.quit()

[end of estimator/__init__.py]
