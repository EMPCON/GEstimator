from cx_Freeze import setup, Executable
import sys
import os

# Define the base for a GUI application on Windows
base = None
if sys.platform == "win32":
    base = "Win32GUI"

# List of executables
executables = [
    Executable(
        script="gestimator.py",
        target_name="GEstimator.exe", # .exe will be added on Windows
        base=base,
        icon=None # Can add path to .ico file here for Windows
    )
]

# Include data files: .glade files and measurement templates
# Format: list of tuples (source_path, destination_path_in_build)
include_files = [
    ('estimator/interface', 'estimator/interface'),
    ('estimator/meas_templates', 'estimator/meas_templates'),
]

# Add GTK data files - this is often necessary for themes, icons, schemas
# These paths are typical for Linux. Adjust if building on/for Windows.
if sys.platform != "win32":
    # GSettings schemas
    if os.path.exists('/usr/share/glib-2.0/schemas'):
        include_files.append(('/usr/share/glib-2.0/schemas', 'share/glib-2.0/schemas'))
    # Icons (Adwaita is a common default, include others if needed)
    if os.path.exists('/usr/share/icons/Adwaita'):
        include_files.append(('/usr/share/icons/Adwaita', 'share/icons/Adwaita'))
    if os.path.exists('/usr/share/icons/gnome'):
         include_files.append(('/usr/share/icons/gnome', 'share/icons/gnome'))
    # GTK resources (like gtkbuilder.glade) - might be needed by some themes/components
    # This path is more variable. Let's try a common one.
    # if os.path.exists('/usr/share/gtk-3.0/'):
    #     include_files.append(('/usr/share/gtk-3.0/', 'share/gtk-3.0/'))


# Dependencies that cx_Freeze might not auto-detect
build_exe_options = {
    "packages": [
        "os", "sys", "logging", "decimal", "hashlib", "threading", "queue",
        "tempfile", "shutil", "importlib", "math", "pickle", "codecs", "json", "re",
        "gi", "openpyxl", "peewee", "appdirs", "prettytable", "cairo" # Added cairo here
    ],
    "includes": [
        "gi.repository.Gtk", "gi.repository.Gdk", "gi.repository.GLib",
        "gi.repository.GObject", "gi.repository.Gio", "gi.repository.Pango",
        "cairo._cairo", # Explicitly include cairo's C extension
        # Add other submodules if specific import errors occur
        "estimator", # Include the main application package
        "estimator.data",
        "estimator.data.measurement",
        "estimator.data.schedule",
        "estimator.interface", # Though .glade files are copied, Python might import from here
        "estimator.meas_templates",
        "estimator.undo",
        "estimator.view",
        "estimator.view.dialogs",
        "estimator.view.dialogs.quick_add_resource_dialog",
        "estimator.view.dialogs.date_edit_dialog",
        "estimator.view.dialogs.add_dependency_dialog",
        "estimator.view.dialogs.analysis_settings_dialog",
        "estimator.view.dialogs.project_settings_dialog",
        "estimator.view.dialogs.program_settings_dialog",
        "estimator.view.dialogs.resource_entry_dialog",
        "estimator.view.dialogs.resource_usage_dialog",
        "estimator.view.dialogs.schedule_dialog",
        "estimator.view.dialogs.select_resource_dialog",
        "estimator.view.dialogs.select_schedule_dialog",
        "estimator.view.dialogs.user_data_dialog",
        "estimator.view.analysis",
        "estimator.view.measurement",
        "estimator.view.project",
        "estimator.view.resource",
        "estimator.view.schedule",
        "estimator.view.cellrenderercustomtext"
    ],
    "include_files": include_files,
    "excludes": ["tkinter"], # tkinter is often not needed
    "zip_include_packages": "*",
    "zip_exclude_packages": [],
    # "include_msvcr": True, # Only for Windows if MSVC runtime needed
    # "optimize": 2, # Can try optimization later
}

setup(
    name="GEstimator",
    version="0.1.0",
    description="GEstimator Application",
    options={"build_exe": build_exe_options},
    executables=executables
)
