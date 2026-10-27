"""Entry point: run the CONVERTOR-APP main GUI window.

Windows:  python main.py

The main window is the full local control panel (file conversions,
text paste, timestamped log). The floating widget is available from
it as the quick path ("Floating widget: show / hide").
"""

from beaver.gui import main

if __name__ == "__main__":
    raise SystemExit(main())
