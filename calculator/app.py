"""Everyday Calculator — a safe, standard-library desktop calculator."""
import ast
import json
import math
import operator
from pathlib import Path
import re
import tkinter as tk
from tkinter import ttk

APP_BG = "#111827"
CARD = "#1c263a"
INK = "#f3f5fb"
MUTED = "#9ba5bd"
BLUE = "#4388f5"
GLASS_EDGE = "#526484"


class GlassButton(tk.Canvas):
    """Rounded, softly highlighted button drawn on a canvas for consistent corners."""

    def __init__(self, parent, text, command, accent=False, width=110, height=42):
        self.label = text
        self.command = command
        self.accent = accent
        self.normal = BLUE if accent else "#27344d"
        self.hover = "#5b9aff" if accent else "#354462"
        self._scale = 1.0
        self._animation_id = None
        self._animation_start = 1.0
        self._animation_target = 1.0
        self._animation_step = 0
        try:
            parent_bg = parent.cget("background")
        except tk.TclError:
            parent_bg = CARD
        if not parent_bg:
            parent_bg = CARD
        super().__init__(parent, width=width, height=height, bg=parent_bg,
                         highlightthickness=0, bd=0, cursor="hand2", takefocus=True)
        self.bind("<Configure>", lambda _event: self._draw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", lambda _event: self.command())
        self.bind("<Return>", lambda _event: self.command())
        self.bind("<space>", lambda _event: self.command())
        self._draw()

    def _draw(self):
        self.delete("all")
        canvas_w, canvas_h = max(self.winfo_width(), 30), max(self.winfo_height(), 28)
        w, h = (canvas_w - 10) * self._scale, (canvas_h - 10) * self._scale
        x0, y0 = (canvas_w - w) / 2, (canvas_h - h) / 2
        r = min(14 * self._scale, h / 2 - 1, w / 2 - 1)
        points = [x0+r, y0, x0+w-r, y0, x0+w, y0, x0+w, y0+r,
                  x0+w, y0+h-r, x0+w, y0+h, x0+w-r, y0+h, x0+r, y0+h,
                  x0, y0+h, x0, y0+h-r, x0, y0+r, x0, y0]
        fill = self.hover if getattr(self, "_hovered", False) else self.normal
        self.create_polygon(points, smooth=True, splinesteps=18, fill=fill,
                            outline=GLASS_EDGE if not self.accent else "#83b4ff", width=1)
        # A fine top rim gives the flat Tk canvas a glass-like highlight.
        self.create_line(x0+r+5, y0+1, x0+w-r-5, y0+1,
                         fill="#a7c8ff" if self.accent else "#697c9f", width=1)
        self.create_text(canvas_w/2, canvas_h/2+1, text=self.label,
                         fill="white" if self.accent else INK,
                         font=("Segoe UI", max(9, round(10*self._scale)), "bold" if self.accent else "normal"))

    def _animate_to(self, target):
        if self._animation_id is not None:
            self.after_cancel(self._animation_id)
        self._animation_start = self._scale
        self._animation_target = target
        self._animation_step = 0
        self._animate_step()

    def _animate_step(self):
        self._animation_step += 1
        progress = min(self._animation_step / 8, 1)
        eased = 1 - (1 - progress) ** 3
        self._scale = self._animation_start + (self._animation_target - self._animation_start) * eased
        self._draw()
        if progress < 1:
            self._animation_id = self.after(15, self._animate_step)
        else:
            self._animation_id = None

    def _on_enter(self, _event):
        self._hovered = True
        self._draw()
        self._animate_to(1.06)

    def _on_leave(self, _event):
        self._hovered = False
        self._draw()
        self._animate_to(1.0)


def calculate(expression):
    """Evaluate arithmetic via a strict AST allow-list (never eval user text)."""
    expression = expression.strip().replace("×", "*").replace("÷", "/").replace("−", "-").replace("^", "**")
    # Accept common algebra shorthand such as 4x, 3(2 + 1), and (2)(3).
    expression = re.sub(r"(?<=\d)(?=x\b)", "*", expression)
    expression = re.sub(r"(?<=\d)(?=\()", "*", expression)
    expression = re.sub(r"(?<=\))(?=\()", "*", expression)
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
    def f(x):
        value = f"({x})"
        left = re.sub(r"(?<![A-Za-z_])x(?![A-Za-z_])", value, sides[0])
        right = re.sub(r"(?<![A-Za-z_])x(?![A-Za-z_])", value, sides[1])
        return calculate(left) - calculate(right)
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
        self.geometry("1080x780")
        self.minsize(850, 650)
        self.configure(bg=APP_BG)
        self._style()
        self._build()

    def _style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=APP_BG)
        style.configure("Card.TFrame", background=CARD, bordercolor="#33415d", lightcolor="#394a69", darkcolor="#182136")
        style.configure("TLabel", background=APP_BG, foreground=INK, font=("Segoe UI", 10))
        style.configure("Card.TLabel", background=CARD, foreground=INK, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=APP_BG, foreground=INK, font=("Segoe UI", 23, "bold"))
        style.configure("Sub.TLabel", background=APP_BG, foreground=MUTED, font=("Segoe UI", 10))
        style.configure("CardTitle.TLabel", background=CARD, foreground=INK, font=("Segoe UI", 14, "bold"))
        style.configure("TButton", background="#303851", foreground=INK, borderwidth=0,
                        font=("Segoe UI", 10), padding=(13, 10))
        style.map("TButton", background=[("active", "#3a4563")], foreground=[("active", "white")])
        style.configure("Accent.TButton", background=BLUE, foreground="white", borderwidth=0,
                        font=("Segoe UI", 10, "bold"), padding=(14, 10))
        style.map("Accent.TButton", background=[("active", "#3476df")])
        style.configure("TNotebook", background=APP_BG, borderwidth=0, tabmargins=(2, 6, 2, 0))
        style.configure("TNotebook.Tab", padding=(18, 12), font=("Segoe UI", 10, "bold"),
                        background="#202c43", foreground=MUTED, borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", "#2a3954"), ("active", "#34445f")],
                  foreground=[("selected", "#8fc0ff"), ("active", INK)])
        style.configure("TEntry", fieldbackground="#2b3249", foreground=INK,
                        insertcolor=INK, borderwidth=0, padding=10)
        style.configure("TCombobox", fieldbackground="#2b3249", background="#2b3249",
                        foreground=INK, arrowcolor=INK, borderwidth=0, padding=7)
        style.map("TCombobox", fieldbackground=[("readonly", "#2b3249")],
                  foreground=[("readonly", INK)], selectbackground=[("readonly", "#2b3249")],
                  selectforeground=[("readonly", INK)])

    def _build(self):
        self.user_name = tk.StringVar()
        self.active_view = "welcome"

        header = ttk.Frame(self, padding=(30, 22, 30, 8)); header.pack(fill="x")
        brand = ttk.Frame(header); brand.pack(anchor="w")
        ttk.Label(brand, text="Everyday Calculator", style="Title.TLabel").pack(side="left")
        self.greeting = ttk.Label(header, text="", style="Sub.TLabel")
        self.greeting.pack(anchor="w", pady=(4, 0))

        self.nav_holder = tk.Frame(self, bg=APP_BG, height=58)
        self.nav_holder.pack(fill="x", padx=30, pady=(2, 8))
        self.view = ttk.Frame(self, padding=(30, 8, 30, 26))
        self.view.pack(fill="both", expand=True)
        self._show_welcome()

    def _clear_view(self):
        for child in self.view.winfo_children():
            child.destroy()

    def _render_nav(self, active):
        for child in self.nav_holder.winfo_children():
            child.destroy()
        bar = tk.Frame(self.nav_holder, bg=APP_BG)
        bar.pack(anchor="center")
        GlassButton(bar, "Calculator", self._show_calculator, accent=active == "calculator", width=170, height=48).pack(side="left", padx=5)
        GlassButton(bar, "Converter", self._show_converters, accent=active == "converter", width=170, height=48).pack(side="left", padx=5)

    def _show_welcome(self):
        self._clear_view()
        for child in self.nav_holder.winfo_children():
            child.destroy()
        self.greeting.configure(text="Your everyday maths companion")
        welcome = ttk.Frame(self.view, padding=46)
        welcome.pack(expand=True)
        ttk.Label(welcome, text="Let's make this yours", style="Title.TLabel").pack(anchor="w")
        ttk.Label(welcome, text="What should I call you?", style="Sub.TLabel").pack(anchor="w", pady=(8, 20))
        entry = ttk.Entry(welcome, textvariable=self.user_name, font=("Segoe UI", 16), width=32)
        entry.pack(fill="x", ipady=9)
        GlassButton(welcome, "Start calculating", self._start, accent=True, width=180, height=48).pack(anchor="w", pady=(20, 0))
        entry.bind("<Return>", lambda _event: self._start())
        entry.focus_set()

    def _start(self):
        name = self.user_name.get().strip()
        if not name:
            self.bell()
            return
        self.user_name.set(name[:24])
        self.greeting.configure(text=f"Hello, {self.user_name.get()}.")
        self._show_calculator()

    def _show_calculator(self):
        if not self.user_name.get().strip():
            self._show_welcome()
            return
        self.active_view = "calculator"
        self._clear_view()
        self._render_nav("calculator")
        page = ttk.Frame(self.view)
        page.pack(fill="both", expand=True)
        self._calculator(page)

    def _show_converters(self):
        if not self.user_name.get().strip():
            self._show_welcome()
            return
        self.active_view = "converter"
        self._clear_view()
        self._render_nav("converter")
        ttk.Label(self.view, text="Choose a converter", style="CardTitle.TLabel", font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(4, 2))
        ttk.Label(self.view, text="Choose a rounded card to open a converter.", style="Sub.TLabel").pack(anchor="w", pady=(0, 16))
        grid = tk.Frame(self.view, bg=APP_BG)
        grid.pack(fill="both", expand=True)
        for column in range(2):
            grid.grid_columnconfigure(column, weight=1)
        cards = [
            ("Currency", "USD to INR", self._show_currency),
            ("Mass", "kg to lb  •  g to oz", self._show_mass),
            ("Gravity", "m/s² to standard g", self._show_gravity),
            ("Data size", "Bits to KB  •  MB to GB", self._show_data),
        ]
        for index, (title, hint, command) in enumerate(cards):
            card = tk.Frame(grid, bg=CARD, highlightbackground=GLASS_EDGE, highlightthickness=1)
            card.grid(row=index // 2, column=index % 2, sticky="nsew", padx=8, pady=8)
            GlassButton(card, title, command, accent=index == 0, width=280, height=68).pack(fill="x", padx=18, pady=(18, 6))
            tk.Label(card, text=hint, fg=MUTED, bg=CARD, font=("Segoe UI", 10)).pack(anchor="w", padx=26, pady=(0, 20))

    def _show_converter_detail(self, builder, label):
        self._clear_view()
        self._render_nav("converter")
        top = tk.Frame(self.view, bg=APP_BG)
        top.pack(fill="x", pady=(2, 10))
        GlassButton(top, "Back", self._show_converters, width=84, height=40).pack(side="left", padx=(0, 12))
        ttk.Label(top, text=label, style="CardTitle.TLabel").pack(side="left")
        page = ttk.Frame(self.view)
        page.pack(fill="both", expand=True)
        builder(page)

    def _show_currency(self): self._show_converter_detail(self._currency, "Currency")
    def _show_mass(self): self._show_converter_detail(self._mass, "Mass")
    def _show_gravity(self): self._show_converter_detail(self._gravity, "Gravity")
    def _show_data(self): self._show_converter_detail(self._data, "Data size")

    def card(self, parent, title, note):
        box = ttk.Frame(parent, style="Card.TFrame", padding=24, borderwidth=1, relief="solid"); box.pack(fill="x", pady=(0, 15))
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
        GlassButton(row, "Calculate", self._calc, accent=True, width=124).pack(side="left", padx=(0, 9))
        GlassButton(row, "Solve for x", self._solve, width=124).pack(side="left")
        self.calc_result = tk.StringVar(value="Your answer will appear here.")
        self._result(box, self.calc_result)
        keypad = ttk.Frame(box, style="Card.TFrame", padding=(0, 18, 0, 2)); keypad.pack(fill="x")
        keys = [["7", "8", "9", "÷", "AC"], ["4", "5", "6", "×", "⌫"],
                ["1", "2", "3", "−", "+"], ["(", "0", ")", ".", "="]]
        for col_index in range(5): keypad.grid_columnconfigure(col_index, weight=1)
        for row_index, key_row in enumerate(keys):
            for col_index, key in enumerate(key_row):
                is_operator = key in {"÷", "×", "−", "+", "="}
                button = GlassButton(keypad, key, lambda value=key: self._key(value),
                                     accent=is_operator, width=90, height=46)
                button.grid(row=row_index, column=col_index, sticky="ew", padx=4, pady=4)
        funcs = self.card(page, "Supported functions", "sin, cos, tan use radians. You can also use asin, acos, atan, log, ln, abs, round, floor, ceil, exp, pi, and e.")
        ttk.Label(funcs, text="Use * for multiplication, / for division, and ^ for powers. Expressions are evaluated safely.", style="Card.TLabel", foreground=MUTED, wraplength=730).pack(anchor="w")

    def _calc(self):
        try:
            if "=" in self.expr.get():
                self.calc_result.set(solve_equation(self.expr.get()))
            else:
                self.calc_result.set(f"= {calculate(self.expr.get())}")
        except Exception as e: self.calc_result.set(f"Check the expression: {e}")

    def _key(self, key):
        if key == "AC": self.expr.set("")
        elif key == "⌫": self.expr.set(self.expr.get()[:-1])
        elif key == "=": self._calc()
        else: self.expr.set(self.expr.get() + {"÷": "/", "×": "*", "−": "-"}.get(key, key))
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
        GlassButton(box, "Convert", lambda: self._convert(convert_fn, amount_var, from_var, to_var, result_var),
                    accent=True, width=126).pack(anchor="w", pady=(18, 0))
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
        GlassButton(buttons, "Convert", self._currency_convert, accent=True, width=114).pack(side="left", padx=(0, 9))
        GlassButton(buttons, "Refresh rates online", self._refresh_rates, width=176).pack(side="left")
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

