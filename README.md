# GEstimator

GEstimator is a Python-based application for project estimation, scheduling, and takeoffs.

## Prerequisites

*   **Python 3:** (Python 3.8 or newer recommended)
*   **Git:** For cloning the repository.
*   **GTK+ 3 and PyGObject:** For the graphical user interface.

## Setup Instructions (Linux Example)

These instructions are primarily for Debian/Ubuntu and Fedora-based Linux distributions. Setting up GTK-based Python applications on Windows or macOS can be more complex and typically involves using environments like MSYS2 (for Windows) or Homebrew (for macOS) to install GTK.

**1. Clone the Repository:**

   Open your terminal and navigate to the directory where you want to store the project. Then run:
   ```bash
   git clone https://github.com/EMPCON/GEstimator.git
   cd GEstimator
   ```
   If the latest features are on a specific branch (e.g., `feature-enhancements-phase1`), check it out:
   ```bash
   # git checkout feature-enhancements-phase1
   ```

**2. Install GTK+ and PyGObject System Dependencies:**

   *   **Debian/Ubuntu:**
      ```bash
      sudo apt update
      sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 libgtk-3-dev
      ```
   *   **Fedora:**
      ```bash
      sudo dnf install python3-gobject gtk3-devel
      ```
   *(Note: Exact package names might vary slightly based on your distribution version.)*

**3. Create and Activate a Python Virtual Environment (Recommended):**

   In the project's root directory (`GEstimator`):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
   *(Your shell prompt should change to indicate the active virtual environment.)*

**4. Install Python Dependencies:**

   With the virtual environment active, install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

## Running GEstimator

Once the setup is complete:

1.  Ensure you are in the project's root directory (`GEstimator`).
2.  Ensure your virtual environment is activated (`source venv/bin/activate`).
3.  Run the application:
    ```bash
    python gestimator.py
    ```

This will launch the GEstimator application window.

---

This README provides basic setup instructions. For detailed feature information, please refer to the application's interface and any accompanying documentation.
