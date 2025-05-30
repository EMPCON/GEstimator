import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import datetime

class DateEditDialog(Gtk.Dialog):
    def __init__(self, parent, current_date_str=None):
        super().__init__(title="Select Date", transient_for=parent, flags=0)
        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK
        )

        self.set_default_size(250, 200)
        self.set_border_width(10)

        self.calendar = Gtk.Calendar()
        self.calendar.set_display_options(
            Gtk.CalendarDisplayOptions.SHOW_HEADING |
            Gtk.CalendarDisplayOptions.SHOW_DAY_NAMES |
            Gtk.CalendarDisplayOptions.SHOW_WEEK_NUMBERS
        )

        if current_date_str:
            try:
                year, month, day = map(int, current_date_str.split('-'))
                self.calendar.select_month(month - 1, year) # month is 0-indexed
                self.calendar.select_day(day)
            except ValueError:
                # Handle invalid date string, select today
                now = datetime.date.today()
                self.calendar.select_month(now.month - 1, now.year)
                self.calendar.select_day(now.day)
        else:
            now = datetime.date.today()
            self.calendar.select_month(now.month - 1, now.year)
            self.calendar.select_day(now.day)

        self.get_content_area().pack_start(self.calendar, True, True, 0)
        self.show_all()

    def get_selected_date(self):
        year, month, day = self.calendar.get_date()
        return datetime.date(year, month + 1, day) # month is 0-indexed in Gtk.Calendar
