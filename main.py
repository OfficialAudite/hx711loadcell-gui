"""
Entry point for the HX711 GUI app.
"""

import sys
import tkinter as tk

from lib.app_ui import HX711App


def main():
    root = tk.Tk()
    app = HX711App(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.stop_reading(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    sys.exit(main())

