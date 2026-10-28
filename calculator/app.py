"""Everyday Calculator — a safe, standard-library desktop calculator."""
import ast
import math
import operator
import tkinter as tk
from tkinter import ttk, messagebox

APP_BG = "#f3f6fb"
CARD = "#ffffff"
INK = "#17243b"
MUTED = "#69778e"
BLUE = "#356df3"


def calculate(expression):
    """Evaluate arithmetic via a strict AST allow-list (never eval user text)."""
    expression = expression.replace("×", "*").replace("÷", "/").replace("−", "-").replace("^", "**")
    tree = ast.parse(expression, mode="eval")
    binary = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
              ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
              ast.Mod: operator.mod, ast.Pow: operator.pow}
    unary = {ast.UAdd: operator.pos, ast.USub: operator.neg}
    funcs = {"sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
             "asin": math.asin, "acos": math.acos, "atan": math.atan,
             "log": math.log10, "ln": math.log, "abs": abs, "round": round,
             "floor": math.floor, "ceil": math.ceil, "exp": math.exp}
    constants = {"pi": math.pi, "e": math.e, "tau": math.tau}

    def visit(node):
        if isinstance(node, ast.Expression): return visit(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float): return node.value
        if isinstance(node, ast.Name) and node.id in constants: return constants[node.id]
        if isinstance(node, ast.BinOp) and type(node.op) in binary:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 1000: raise ValueError("Exponent is too large.")
            return binary[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in unary: return unary[type(node.op)](visit(node.operand))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in funcs and not node.keywords:
            return funcs[node.func.id](*(visit(arg) for arg in node.args))
        raise ValueError("Use numbers, + − × ÷, parentheses, ^, pi, e, or a supported function.")

    result = visit(tree)
    if isinstance(result, complex): return result
    if not math.isfinite(result): raise ValueError("Result is outside the supported range.")
    return result


def solve_equation(text):
    sides = text.replace("=", " = ").split("=")
    if len(sides) != 2: raise ValueError("Enter one equation with one equals sign, such as 2*x + 3 = 11.")
    # Determine polynomial coefficients by evaluating at x=0, 1, -1, 2.
    def f(x): return calculate(sides[0].replace("x", f"({x})")) - calculate(sides[1].replace("x", f"({x})"))
    y0, y1, ym1, y2 = (f(v) for v in (0, 1, -1, 2))
    a = (y1 + ym1 - 2*y0) / 2
    b = (y1 - ym1) / 2
    c = y0
    if abs(f(3) - (9*a + 3*b + c)) > 1e-8: raise ValueError("This solver supports linear and quadratic equations in x.")
    if abs(a) < 1e-12:
        if abs(b) < 1e-12:
            return "Every x is a solution." if abs(c) < 1e-12 else "No solution."
        return f"x = {-c/b:.12g}  (linear equation)"
    d = b*b - 4*a*c
    if d < -1e-12: return f"No real solutions (discriminant = {d:.6g})."
    if abs(d) <= 1e-12: return f"x = {-b/(2*a):.12g}  (one repeated solution)"
    x1, x2 = (-b + math.sqrt(d))/(2*a), (-b - math.sqrt(d))/(2*a)
    return f"x₁ = {x1:.12g}\nx₂ = {x2:.12g}  (quadratic equation)"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Everyday Calculator")
        self.geometry("940x720")
        self.minsize(800, 630)
        self.configure(bg=APP_BG)
        self._style()
        self._build()

    def _style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=APP_BG)
        style.configure("Card.TFrame", background=CARD)
        style.configure("TLabel", background=APP_BG, foreground=INK, font=("Segoe UI", 10))
        style.configure("Card.TLabel", background=CARD, foreground=INK, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=APP_BG, foreground=INK, font=("Segoe UI", 23, "bold"))
        style.configure("Sub.TLabel", background=APP_BG, foreground=MUTED, font=("Segoe UI", 10))
        style.configure("CardTitle.TLabel", background=CARD, foreground=INK, font=("Segoe UI", 14, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 9))
        style.configure("Accent.TButton", background=BLUE, foreground="white", font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#2458d5")])
        style.configure("TNotebook", background=APP_BG, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(17, 11), font=("Segoe UI", 10, "bold"), background="#e8edf6")
        style.map("TNotebook.Tab", background=[("selected", CARD)], foreground=[("selected", BLUE)])

    def _build(self):
        header = ttk.Frame(self, padding=(30, 22, 30, 14)); header.pack(fill="x")
        ttk.Label(header, text="Everyday Calculator", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="Calculate, solve equations, and convert everyday units.", style="Sub.TLabel").pack(anchor="w", pady=(3, 0))
        self.tabs = ttk.Notebook(self); self.tabs.pack(fill="both", expand=True, padx=26, pady=(4, 24))
        for title, builder in [("Calculator", self._calculator), ("Currency", self._currency), ("Mass", self._mass), ("Gravity", self._gravity), ("Data size", self._data)]:
            page = ttk.Frame(self.tabs, padding=24); self.tabs.add(page, text=title); builder(page)

    def card(self, parent, title, note):
        box = ttk.Frame(parent, style="Card.TFrame", padding=24); box.pack(fill="x", pady=(0, 15))
        ttk.Label(box, text=title, style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(box, text=note, style="Card.TLabel", foreground=MUTED).pack(anchor="w", pady=(5, 18))
        return box

    def _result(self, parent, variable):
        ttk.Label(parent, textvariable=variable, style="Card.TLabel", foreground=BLUE, font=("Segoe UI", 12, "bold"), wraplength=700).pack(anchor="w", pady=(17, 0))

    def _calculator(self, page):
        box = self.card(page, "Calculator & equation solver", "Type an expression or solve a linear / quadratic equation in x.")
        self.expr = tk.StringVar()
        ent = ttk.Entry(box, textvariable=self.expr, font=("Segoe UI", 16), width=48); ent.pack(fill="x", ipady=8); ent.bind("<Return>", lambda _: self._calc())
        ttk.Label(box, text="Examples:  (12 + 8) / 4     •     sqrt(81) + pi     •     2*x^2 - 5*x + 2 = 0", style="Card.TLabel", foreground=MUTED).pack(anchor="w", pady=(9, 14))
        row = ttk.Frame(box, style="Card.TFrame"); row.pack(anchor="w")
        ttk.Button(row, text="Calculate", style="Accent.TButton", command=self._calc).pack(side="left", padx=(0, 8))
        ttk.Button(row, text="Solve for x", command=self._solve).pack(side="left")
        self.calc_result = tk.StringVar(value="Your answer will appear here."); self._result(box, self.calc_result)
        funcs = self.card(page, "Supported functions", "sin, cos, tan use radians. You can also use asin, acos, atan, log, ln, abs, round, floor, ceil, exp, pi, and e.")
        ttk.Label(funcs, text="Use * for multiplication, / for division, and ^ for powers. Expressions are evaluated safely.", style="Card.TLabel", foreground=MUTED, wraplength=730).pack(anchor="w")

    def _calc(self):
        try: self.calc_result.set(f"= {calculate(self.expr.get())}")
        except Exception as e: self.calc_result.set(f"Check the expression: {e}")
    def _solve(self):
        try: self.calc_result.set(solve_equation(self.expr.get()))
        except Exception as e: self.calc_result.set(f"Could not solve: {e}")

    def _converter(self, page, title, note, units, convert_fn=None):
        box = self.card(page, title, note)
        row = ttk.Frame(box, style="Card.TFrame"); row.pack(fill="x")
        amount_var = tk.StringVar(value="1")
        ttk.Entry(row, textvariable=amount_var, width=16, font=("Segoe UI", 13)).pack(side="left", ipady=5, padx=(0, 9))
        from_var = tk.StringVar(value=units[0]); to_var = tk.StringVar(value=units[1])
        ttk.Combobox(row, textvariable=from_var, values=units, state="readonly", width=18).pack(side="left", padx=5, ipady=4)
        ttk.Label(row, text="to", style="Card.TLabel", foreground=MUTED).pack(side="left", padx=8)
        ttk.Combobox(row, textvariable=to_var, values=units, state="readonly", width=18).pack(side="left", padx=5, ipady=4)
        result_var = tk.StringVar(value="Converted result will appear here.")
        ttk.Button(box, text="Convert", style="Accent.TButton", command=lambda: self._convert(convert_fn, amount_var, from_var, to_var, result_var)).pack(anchor="w", pady=(18, 0))
        self._result(box, result_var)

    def _convert(self, fn, amount_var, from_var, to_var, result_var):
        try:
            amount = float(amount_var.get().replace(",", ""))
            value, suffix = fn(amount, from_var.get(), to_var.get())
            result_var.set(f"{amount:g} {from_var.get()} = {value:,.10g} {to_var.get()}{suffix}")
        except Exception as e: result_var.set(f"Could not convert: {e}")

    def _mass(self, page):
        units = ["kg", "g", "mg", "tonne", "lb", "oz", "stone"]
        factors = {"kg":1, "g":.001, "mg":1e-6, "tonne":1000, "lb":.45359237, "oz":.028349523125, "stone":6.35029318}
        self._converter(page, "Mass converter", "Convert between metric and imperial mass units.", units, lambda n,a,b:(n*factors[a]/factors[b], ""))

    def _gravity(self, page):
        units = ["m/s²", "standard g", "ft/s²", "Gal (cm/s²)"]
        factors = {"m/s²":1, "standard g":9.80665, "ft/s²":.3048, "Gal (cm/s²)":.01}
        self._converter(page, "Gravity / acceleration converter", "Convert gravitational acceleration between common units. Standard gravity = 9.80665 m/s².", units, lambda n,a,b:(n*factors[a]/factors[b], ""))

    def _data(self, page):
        units = ["bit", "byte", "KB (1000 B)", "MB (1000 KB)", "GB (1000 MB)", "TB (1000 GB)", "KiB (1024 B)", "MiB (1024 KiB)", "GiB (1024 MiB)", "TiB (1024 GiB)"]
        factors = {"bit":1/8, "byte":1, "KB (1000 B)":1000, "MB (1000 KB)":1e6, "GB (1000 MB)":1e9, "TB (1000 GB)":1e12, "KiB (1024 B)":1024, "MiB (1024 KiB)":1024**2, "GiB (1024 MiB)":1024**3, "TiB (1024 GiB)":1024**4}
        self._converter(page, "Data size converter", "Convert bit and byte sizes. KB/MB use decimal units; KiB/MiB use binary units.", units, lambda n,a,b:(n*factors[a]/factors[b], ""))

    def _currency(self, page):
        units = ["USD", "EUR", "GBP", "INR", "JPY", "CAD", "AUD", "CHF", "CNY", "SGD"]
        box = self.card(page, "Currency converter", "Rates are illustrative starter values. Edit them or refresh online when internet access is available.")
        row = ttk.Frame(box, style="Card.TFrame"); row.pack(fill="x")
        self.amount = tk.StringVar(value="1")
        ttk.Entry(row, textvariable=self.amount, width=16, font=("Segoe UI", 13)).pack(side="left", ipady=5, padx=(0, 9))
        self.from_unit = tk.StringVar(value="USD"); self.to_unit = tk.StringVar(value="INR")
        ttk.Combobox(row, textvariable=self.from_unit, values=units, state="readonly", width=12).pack(side="left", padx=5, ipady=4)
        ttk.Label(row, text="to", style="Card.TLabel", foreground=MUTED).pack(side="left", padx=8)
        ttk.Combobox(row, textvariable=self.to_unit, values=units, state="readonly", width=12).pack(side="left", padx=5, ipady=4)
        self.rates = {"USD":1, "EUR":.92, "GBP":.79, "INR":83.5, "JPY":150, "CAD":1.36, "AUD":1.52, "CHF":.88, "CNY":7.2, "SGD":1.34}
        self._currency_rates_label = ttk.Label(box, text="Starter rates: 1 USD = 83.5 INR (illustrative).", style="Card.TLabel", foreground=MUTED, wraplength=700); self._currency_rates_label.pack(anchor="w", pady=(15, 0))
        buttons = ttk.Frame(box, style="Card.TFrame"); buttons.pack(anchor="w", pady=(17, 0))
        ttk.Button(buttons, text="Convert", style="Accent.TButton", command=self._currency_convert).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Refresh rates online", command=self._refresh_rates).pack(side="left")
        self.convert_result = tk.StringVar(value="Converted result will appear here."); self._result(box, self.convert_result)
        ttk.Label(page, text="Exchange rates can change throughout the day. Check the displayed update status before relying on a conversion.", style="Sub.TLabel", wraplength=700).pack(anchor="w", pady=5)

    def _currency_convert(self):
        try:
            amount = float(self.amount.get().replace(",", "")); a, b = self.from_unit.get(), self.to_unit.get()
            value = amount * self.rates[b] / self.rates[a]
            self.convert_result.set(f"{amount:g} {a} = {value:,.8g} {b}")
        except Exception as e: self.convert_result.set(f"Could not convert: {e}")

    def _refresh_rates(self):
        import threading, urllib.request, json
        def fetch():
            try:
                with urllib.request.urlopen("https://open.er-api.com/v6/latest/USD", timeout=8) as response:
                    data = json.loads(response.read().decode("utf-8"))
                if data.get("result") != "success": raise ValueError("Rate service did not return current rates.")
                rates = {code: float(data["rates"][code]) for code in self.rates}
                def apply():
                    self.rates.update(rates)
                    self._currency_rates_label.configure(text=f"Online rates updated: {data.get('time_last_update_utc', 'current')} (base USD).")
                    self._currency_convert()
                self.after(0, apply)
            except Exception as e:
                self.after(0, lambda: self._currency_rates_label.configure(text=f"Could not refresh rates: {e} Check your internet connection."))
        threading.Thread(target=fetch, daemon=True).start()


if __name__ == "__main__":
    App().mainloop()

