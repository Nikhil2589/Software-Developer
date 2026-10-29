# Everyday Calculator

A dark, card-based desktop calculator built with Python and Tkinter. It includes a keypad, safe arithmetic calculator, a linear and quadratic equation solver, and currency, mass, gravitational acceleration, and data size converters.

## Run

1. Install Python 3.10 or later. Tkinter is included with the standard Windows and macOS installers.
2. Open a terminal in this folder and run:

   ```text
   python app.py
   ```

The currency tab starts with clearly marked illustrative rates. Choose **Refresh rates online** to load current rates from open.er-api.com; internet access is needed. Other converters work offline.

## Calculator notes

Use `+`, `-`, `*`, `/`, `//`, `%`, `^`, and parentheses. Supported functions include `sqrt`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `log`, `ln`, `abs`, `round`, `floor`, `ceil`, and `exp`; `sin`/`cos`/`tan` use radians. The equation solver accepts equations in `x` with degree at most two, for example `2*x^2 - 5*x + 2 = 0`.

Data sizes distinguish decimal KB/MB (powers of 1000) from binary KiB/MiB (powers of 1024). The gravity tab converts acceleration units, using standard gravity of 9.80665 m/s².

