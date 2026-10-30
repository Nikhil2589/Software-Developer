"""Everyday Calculator for Android. Built with Kivy and packaged with Buildozer."""
__version__ = "1.1.0"

import ast
import json
import math
import operator
import os
import re
import threading
import urllib.request

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, PopMatrix, PushMatrix, RoundedRectangle, Scale, Translate
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, ListProperty, NumericProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivy.storage.jsonstore import JsonStore
from kivy.utils import escape_markup


COLORS = {
    "background": (0.045, 0.065, 0.105, 1),
    "panel": (0.085, 0.12, 0.19, 0.97),
    "panel_inner": (0.105, 0.15, 0.23, 0.98),
    "edge": (0.34, 0.45, 0.64, 0.8),
    "blue": (0.20, 0.46, 0.91, 1),
    "blue_edge": (0.54, 0.73, 1, 0.95),
    "text": (0.95, 0.97, 1, 1),
    "muted": (0.62, 0.69, 0.81, 1),
    "green": (0.37, 0.78, 0.55, 1),
}


def calculate(expression):
    """Evaluate an arithmetic expression without using eval()."""
    expression = expression.strip().replace("×", "*").replace("÷", "/").replace("−", "-").replace("^", "**")
    expression = re.sub(r"(?<=\d)(?=x\b)", "*", expression)
    expression = re.sub(r"(?<=\d)(?=\()", "*", expression)
    expression = re.sub(r"(?<=\))(?=\()", "*", expression)
    tree = ast.parse(expression, mode="eval")
    binary = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
              ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
              ast.Mod: operator.mod, ast.Pow: operator.pow}
    unary = {ast.UAdd: operator.pos, ast.USub: operator.neg}
    functions = {"sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
                 "asin": math.asin, "acos": math.acos, "atan": math.atan,
                 "log": math.log10, "ln": math.log, "abs": abs, "round": round,
                 "floor": math.floor, "ceil": math.ceil, "exp": math.exp}
    constants = {"pi": math.pi, "e": math.e, "tau": math.tau}

    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.Name) and node.id in constants:
            return constants[node.id]
        if isinstance(node, ast.BinOp) and type(node.op) in binary:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 1000:
                raise ValueError("Exponent is too large.")
            return binary[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in unary:
            return unary[type(node.op)](visit(node.operand))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in functions and not node.keywords:
            return functions[node.func.id](*(visit(arg) for arg in node.args))
        raise ValueError("Use numbers, + − × ÷, parentheses, ^, pi, e, or a supported function.")

    result = visit(tree)
    if isinstance(result, complex):
        return result
    if not math.isfinite(result):
        raise ValueError("Result is outside the supported range.")
    return result


def solve_equation(equation):
    sides = equation.split("=")
    if len(sides) != 2:
        raise ValueError("Enter one equation with one equals sign, such as 4x^2 + 3x - 5 = 0.")

    def difference(x):
        value = f"({x})"
        left = re.sub(r"(?<![A-Za-z_])x(?![A-Za-z_])", value, sides[0])
        right = re.sub(r"(?<![A-Za-z_])x(?![A-Za-z_])", value, sides[1])
        return calculate(left) - calculate(right)

    y0, y1, ym1, y2 = (difference(v) for v in (0, 1, -1, 2))
    a = (y1 + ym1 - 2 * y0) / 2
    b = (y1 - ym1) / 2
    c = y0
    if abs(difference(3) - (9 * a + 3 * b + c)) > 1e-8:
        raise ValueError("This solver supports linear and quadratic equations in x.")
    if abs(a) < 1e-12:
        if abs(b) < 1e-12:
            return "Every x is a solution." if abs(c) < 1e-12 else "No solution."
        return f"x = {-c / b:.12g}  (linear equation)"
    discriminant = b * b - 4 * a * c
    if discriminant < -1e-12:
        return f"No real solutions (discriminant = {discriminant:.6g})."
    if abs(discriminant) <= 1e-12:
        return f"x = {-b / (2 * a):.12g}  (one repeated solution)"
    root = math.sqrt(discriminant)
    x1, x2 = (-b + root) / (2 * a), (-b - root) / (2 * a)
    return f"x₁ = {x1:.12g}\nx₂ = {x2:.12g}  (quadratic equation)"


class GlassPanel(BoxLayout):
    """A softly layered rounded panel."""

    fill_color = ListProperty(COLORS["panel"])
    edge_color = ListProperty(COLORS["edge"])

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("padding", dp(16))
        kwargs.setdefault("spacing", dp(10))
        super().__init__(**kwargs)
        self.bind(pos=self._paint, size=self._paint, fill_color=self._paint, edge_color=self._paint)
        self._paint()

    def _paint(self, *_args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.edge_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(22)])
            Color(*self.fill_color)
            RoundedRectangle(pos=(self.x + dp(1), self.y + dp(1)),
                             size=(max(0, self.width - dp(2)), max(0, self.height - dp(2))),
                             radius=[dp(21)])


class GlassButton(ButtonBehavior, Label):
    """Rounded glass-style touch button with a small press-pop animation."""

    selected = BooleanProperty(False)
    accent = BooleanProperty(False)
    scale_factor = NumericProperty(1.0)
    fill_color = ListProperty(COLORS["panel_inner"])

    def __init__(self, **kwargs):
        kwargs.setdefault("halign", "center")
        kwargs.setdefault("valign", "middle")
        kwargs.setdefault("color", COLORS["text"])
        kwargs.setdefault("font_size", sp(15))
        kwargs.setdefault("bold", False)
        kwargs.setdefault("markup", True)
        super().__init__(**kwargs)
        self.bind(pos=self._update_canvas, size=self._update_canvas,
                  scale_factor=self._update_scale, selected=self._update_color,
                  accent=self._update_color, state=self._animate_press)
        with self.canvas.before:
            PushMatrix()
            self._translate_center = Translate()
            self._scale = Scale(1, 1, 1)
            self._translate_origin = Translate()
            self._edge_instruction = Color(*COLORS["edge"])
            self._outer = RoundedRectangle(radius=[dp(18)])
            self._fill_instruction = Color(*self.fill_color)
            self._inner = RoundedRectangle(radius=[dp(17)])
        with self.canvas.after:
            PopMatrix()
        self._update_canvas()
        self._update_color()

    def _update_canvas(self, *_args):
        self.text_size = self.size
        self._outer.pos, self._outer.size = self.pos, self.size
        inset = dp(1)
        self._inner.pos = (self.x + inset, self.y + inset)
        self._inner.size = (max(0, self.width - 2 * inset), max(0, self.height - 2 * inset))
        cx, cy = self.center
        self._translate_center.x, self._translate_center.y = cx, cy
        self._translate_origin.x, self._translate_origin.y = -cx, -cy

    def _update_scale(self, *_args):
        self._scale.x = self._scale.y = self.scale_factor

    def _update_color(self, *_args):
        if self.accent or self.selected:
            self._edge_instruction.rgba = COLORS["blue_edge"]
            self.fill_color = (0.18, 0.39, 0.73, 0.98)
        else:
            self._edge_instruction.rgba = COLORS["edge"]
            self.fill_color = COLORS["panel_inner"]
        self._fill_instruction.rgba = self.fill_color

    def _animate_press(self, _instance, state):
        target = 1.045 if state == "down" else 1.0
        Animation.cancel_all(self, "scale_factor")
        Animation(scale_factor=target, duration=0.11, t="out_quad").start(self)


def body_label(text, size=14, color=None, **kwargs):
    label = Label(text=text, markup=True, font_size=sp(size), color=color or COLORS["text"],
                  halign="left", valign="middle", **kwargs)
    label.bind(width=lambda widget, width: setattr(widget, "text_size", (width, None)))
    return label


class CalculatorScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.result = None
        self.expression = None
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3), scroll_type=["bars", "content"])
        content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(12), padding=(0, dp(2), 0, dp(12)))
        content.bind(minimum_height=content.setter("height"))
        scroll.add_widget(content)
        self.add_widget(scroll)

        entry_panel = GlassPanel(size_hint_y=None, height=dp(204))
        entry_panel.add_widget(body_label("Expression or equation", size=14, bold=True, size_hint_y=None, height=dp(22)))
        self.expression = TextInput(hint_text="e.g. 4x^2 + 3x - 5 = 0", multiline=False,
                                    size_hint_y=None, height=dp(50), font_size=sp(19),
                                    foreground_color=COLORS["text"], hint_text_color=COLORS["muted"],
                                    cursor_color=COLORS["blue"], background_normal="",
                                    background_active="", background_color=(0.07, 0.105, 0.17, 1),
                                    padding=(dp(12), dp(14)))
        entry_panel.add_widget(self.expression)
        action_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        action_row.add_widget(GlassButton(text="Calculate", accent=True, on_release=lambda *_: self.calculate()))
        action_row.add_widget(GlassButton(text="Solve for x", on_release=lambda *_: self.solve()))
        entry_panel.add_widget(action_row)
        content.add_widget(entry_panel)

        result_panel = GlassPanel(size_hint_y=None, height=dp(96), padding=dp(14), spacing=dp(5))
        result_panel.add_widget(body_label("RESULT", size=10, color=COLORS["muted"], size_hint_y=None, height=dp(16), bold=True))
        self.result = body_label("Your answer will appear here", size=16, color=(0.56, 0.76, 1, 1))
        result_panel.add_widget(self.result)
        content.add_widget(result_panel)

        keypad_panel = GlassPanel(size_hint_y=None, height=dp(264), padding=dp(12), spacing=dp(8))
        keypad_panel.add_widget(body_label("QUICK KEYPAD", size=10, color=COLORS["muted"], size_hint_y=None, height=dp(17), bold=True))
        keys = GridLayout(cols=5, rows=4, spacing=dp(6))
        for row in [["7", "8", "9", "/", "AC"], ["4", "5", "6", "*", "DEL"],
                    ["1", "2", "3", "-", "+"], ["(", "0", ")", ".", "="]]:
            for key in row:
                keys.add_widget(GlassButton(text=key, accent=key in {"/", "*", "-", "+", "="},
                                            on_release=lambda _btn, value=key: self.key(value)))
        keypad_panel.add_widget(keys)
        content.add_widget(keypad_panel)
        content.add_widget(body_label(
            "Functions: <b>sqrt, sin, cos, tan, log, ln, abs, exp, pi, e</b>  •  Trig uses radians.",
            size=11, color=COLORS["muted"], size_hint_y=None, height=dp(38)))

    def calculate(self):
        try:
            text = self.expression.text.strip()
            self.result.text = solve_equation(text) if "=" in text else f"=  {calculate(text)}"
        except Exception as error:
            self.result.text = f"Check your entry: {error}"

    def solve(self):
        try:
            self.result.text = solve_equation(self.expression.text)
        except Exception as error:
            self.result.text = f"Could not solve: {error}"

    def key(self, key):
        if key == "AC":
            self.expression.text = ""
        elif key == "DEL":
            self.expression.text = self.expression.text[:-1]
        elif key == "=":
            self.calculate()
        else:
            self.expression.text += {"÷": "/", "×": "*", "−": "-"}.get(key, key)


CONVERTERS = {
    "Currency": {"hint": "USD to INR", "units": ["USD", "EUR", "GBP", "INR", "JPY", "CAD", "AUD", "CHF", "CNY", "SGD"], "source": "USD", "target": "INR"},
    "Mass": {"hint": "kg to lb  •  g to oz", "units": ["kg", "g", "mg", "tonne", "lb", "oz", "stone"], "source": "kg", "target": "lb"},
    "Gravity": {"hint": "m/s² to standard g", "units": ["m/s²", "standard g", "ft/s²", "Gal (cm/s²)"], "source": "m/s²", "target": "standard g"},
    "Data size": {"hint": "Bits to KB  •  MB to GB", "units": ["bit", "byte", "KB (1000 B)", "MB (1000 KB)", "GB (1000 MB)", "TB (1000 GB)", "KiB (1024 B)", "MiB (1024 KiB)", "GiB (1024 MiB)", "TiB (1024 GiB)"], "source": "bit", "target": "KB (1000 B)"},
}


class ConverterGridScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(12), padding=(0, dp(4), 0, dp(14)))
        content.bind(minimum_height=content.setter("height"))
        content.add_widget(body_label("Choose a converter", size=20, bold=True, size_hint_y=None, height=dp(34)))
        content.add_widget(body_label("Tap a glass card to open it.", size=12, color=COLORS["muted"], size_hint_y=None, height=dp(24)))
        grid = GridLayout(cols=2, spacing=dp(10), size_hint_y=None, padding=dp(2))
        grid.bind(minimum_height=grid.setter("height"))
        # Keep card marks within the portable Roboto character set used on Android.
        symbols = {"Currency": "$", "Mass": "kg", "Gravity": "g", "Data size": "bit"}
        for name, data in CONVERTERS.items():
            card = GlassButton(text=f"[size=25sp][color=8fc0ff]{symbols[name]}[/color][/size]\n[b]{name}[/b]\n[size=11sp][color=9baac4]{data['hint']}[/color][/size]",
                               size_hint=(1, None), height=dp(148), on_release=lambda _btn, n=name: self.app.open_converter(n))
            grid.add_widget(card)
        content.add_widget(grid)
        scroll.add_widget(content)
        self.add_widget(scroll)


class ConverterDetailScreen(Screen):
    def __init__(self, app, converter_name, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.converter_name = converter_name
        self.config = CONVERTERS[converter_name]
        self.amount = None
        self.source = None
        self.target = None
        self.output = None
        self.status = None
        self._build()

    def _build(self):
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(12), padding=(0, dp(3), 0, dp(12)))
        content.bind(minimum_height=content.setter("height"))
        header = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        header.add_widget(GlassButton(text="Back", size_hint_x=None, width=dp(88), on_release=lambda *_: self.app.back_to_converters()))
        header.add_widget(body_label(self.converter_name, size=20, bold=True))
        content.add_widget(header)

        panel = GlassPanel(size_hint_y=None, height=dp(262), padding=dp(16), spacing=dp(12))
        panel.add_widget(body_label("AMOUNT", size=10, color=COLORS["muted"], size_hint_y=None, height=dp(17), bold=True))
        self.amount = TextInput(text="1", multiline=False, input_filter="float", size_hint_y=None, height=dp(50),
                                font_size=sp(20), foreground_color=COLORS["text"], cursor_color=COLORS["blue"],
                                background_normal="", background_active="", background_color=(0.07, 0.105, 0.17, 1),
                                padding=(dp(12), dp(14)))
        panel.add_widget(self.amount)
        unit_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        units = self.config["units"]
        self.source = self._spinner(self.config["source"], units)
        self.target = self._spinner(self.config["target"], units)
        unit_row.add_widget(self.source)
        unit_row.add_widget(body_label("to", size=13, color=COLORS["blue"], halign="center"))
        unit_row.add_widget(self.target)
        panel.add_widget(unit_row)
        panel.add_widget(GlassButton(text="Convert", accent=True, size_hint_y=None, height=dp(44), on_release=lambda *_: self.convert()))
        content.add_widget(panel)

        result_panel = GlassPanel(size_hint_y=None, height=dp(115), padding=dp(15), spacing=dp(5))
        result_panel.add_widget(body_label("RESULT", size=10, color=COLORS["muted"], size_hint_y=None, height=dp(17), bold=True))
        self.output = body_label("Your converted value will appear here.", size=16, color=(0.56, 0.76, 1, 1))
        result_panel.add_widget(self.output)
        content.add_widget(result_panel)
        content.add_widget(body_label(self._description(), size=11, color=COLORS["muted"], size_hint_y=None, height=dp(46)))
        if self.converter_name == "Currency":
            self.status = body_label("Starter rates are illustrative.", size=10, color=COLORS["muted"], size_hint_y=None, height=dp(26))
            content.add_widget(self.status)
            content.add_widget(GlassButton(text="Refresh exchange rates", size_hint_y=None, height=dp(44), on_release=lambda *_: self.refresh_rates()))
        scroll.add_widget(content)
        self.add_widget(scroll)

    def _spinner(self, initial, values):
        return Spinner(text=initial, values=values, size_hint=(0.44, 1), font_size=sp(12),
                       background_normal="", background_color=(0.12, 0.18, 0.28, 1),
                       color=COLORS["text"])

    def _description(self):
        if self.converter_name == "Gravity":
            return "Standard gravity = 9.80665 m/s². This converts acceleration units."
        if self.converter_name == "Data size":
            return "KB uses 1000 bytes. KiB uses 1024 bytes. Bits are converted to bytes automatically."
        if self.converter_name == "Currency":
            return "Exchange rates change. Refresh rates online before relying on a conversion."
        return "Convert common metric and imperial mass units."

    def convert(self):
        try:
            amount = float(self.amount.text or "0")
            source, target = self.source.text, self.target.text
            if self.converter_name == "Currency":
                value = amount * self.app.rates[target] / self.app.rates[source]
            elif self.converter_name == "Mass":
                factors = {"kg": 1, "g": .001, "mg": 1e-6, "tonne": 1000, "lb": .45359237,
                           "oz": .028349523125, "stone": 6.35029318}
                value = amount * factors[source] / factors[target]
            elif self.converter_name == "Gravity":
                factors = {"m/s²": 1, "standard g": 9.80665, "ft/s²": .3048, "Gal (cm/s²)": .01}
                value = amount * factors[source] / factors[target]
            else:
                factors = {"bit": 1/8, "byte": 1, "KB (1000 B)": 1000, "MB (1000 KB)": 1e6,
                           "GB (1000 MB)": 1e9, "TB (1000 GB)": 1e12, "KiB (1024 B)": 1024,
                           "MiB (1024 KiB)": 1024**2, "GiB (1024 MiB)": 1024**3, "TiB (1024 GiB)": 1024**4}
                value = amount * factors[source] / factors[target]
            self.output.text = f"{amount:g} {source}  =  {value:,.10g} {target}"
        except Exception as error:
            self.output.text = f"Could not convert: {error}"

    def refresh_rates(self):
        self.status.text = "Fetching current rates…"
        def fetch():
            try:
                request = urllib.request.Request("https://open.er-api.com/v6/latest/USD", headers={"User-Agent": "EverydayCalculator/1.0"})
                with urllib.request.urlopen(request, timeout=10) as response:
                    data = json.loads(response.read().decode("utf-8"))
                if data.get("result") != "success":
                    raise ValueError("The rate service did not return current rates.")
                new_rates = {code: float(data["rates"][code]) for code in self.app.rates}
                def apply(_dt):
                    self.app.rates.update(new_rates)
                    self.status.text = f"Rates updated • {data.get('time_last_update_utc', 'current')} (base USD)"
                    self.convert()
                Clock.schedule_once(apply, 0)
            except Exception as error:
                message = str(error)
                Clock.schedule_once(lambda _dt, msg=message: setattr(self.status, "text", f"Refresh failed: {msg}"), 0)
        threading.Thread(target=fetch, daemon=True).start()


class NameSetupScreen(Screen):
    """First-launch name prompt, shown once and saved on the device."""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(14),
                            padding=(0, dp(18), 0, dp(18)))
        content.bind(minimum_height=content.setter("height"))
        content.add_widget(body_label("Let's make this yours", size=25, bold=True,
                                      size_hint_y=None, height=dp(42)))
        content.add_widget(body_label("What should I call you?", size=15,
                                      color=COLORS["muted"], size_hint_y=None, height=dp(30)))
        panel = GlassPanel(size_hint_y=None, height=dp(188))
        panel.add_widget(body_label("YOUR NAME", size=10, color=COLORS["muted"],
                                    size_hint_y=None, height=dp(18), bold=True))
        self.name_input = TextInput(hint_text="Type your name", multiline=False,
                                    size_hint_y=None, height=dp(52), font_size=sp(19),
                                    foreground_color=COLORS["text"], hint_text_color=COLORS["muted"],
                                    cursor_color=COLORS["blue"], background_normal="",
                                    background_active="", background_color=(0.07, 0.105, 0.17, 1),
                                    padding=(dp(12), dp(14)))
        self.name_input.bind(on_text_validate=lambda *_: self.app.start_with_name())
        panel.add_widget(self.name_input)
        self.error = body_label("", size=11, color=(1, .52, .52, 1),
                                size_hint_y=None, height=dp(20))
        panel.add_widget(self.error)
        panel.add_widget(GlassButton(text="Start calculating", accent=True,
                                     size_hint_y=None, height=dp(44),
                                     on_release=lambda *_: self.app.start_with_name()))
        content.add_widget(panel)
        scroll.add_widget(content)
        self.add_widget(scroll)


class EverydayCalculatorApp(App):
    title = "Everyday Calculator"
    rates = {"USD": 1, "EUR": .92, "GBP": .79, "INR": 83.5, "JPY": 150,
             "CAD": 1.36, "AUD": 1.52, "CHF": .88, "CNY": 7.2, "SGD": 1.34}

    def build(self):
        Window.clearcolor = COLORS["background"]
        Window.softinput_mode = "below_target"
        Window.fullscreen = False
        self.settings = JsonStore(os.path.join(self.user_data_dir, "settings.json"))
        self.user_name = self.settings.get("profile").get("name", "") if self.settings.exists("profile") else ""

        root = BoxLayout(orientation="vertical", padding=(dp(14), dp(8), dp(14), dp(8)), spacing=dp(9))
        self.greeting = body_label("", size=25, bold=True, size_hint_y=None, height=dp(43))
        root.add_widget(self.greeting)

        nav = GlassPanel(orientation="horizontal", size_hint_y=None, height=dp(56), padding=dp(5), spacing=dp(6))
        self.calculator_tab = GlassButton(text="Calculator", selected=True, on_release=lambda *_: self.show_tab("Calculator"))
        self.converter_tab = GlassButton(text="Converter", on_release=lambda *_: self.show_tab("Converter"))
        nav.add_widget(self.calculator_tab)
        nav.add_widget(self.converter_tab)
        root.add_widget(nav)
        self.main_nav = nav

        self.screens = ScreenManager(transition=SlideTransition(duration=.20))
        self.screens.add_widget(NameSetupScreen(self, name="name_setup"))
        self.screens.add_widget(CalculatorScreen(self, name="calculator"))
        self.screens.add_widget(ConverterGridScreen(self, name="converter_grid"))
        self.converter_screens = {}
        for converter_name in CONVERTERS:
            screen_name = self._converter_screen_name(converter_name)
            self.screens.add_widget(ConverterDetailScreen(self, converter_name, name=screen_name))
            self.converter_screens[converter_name] = screen_name
        self.screens.bind(current=self._persist_current_screen)
        root.add_widget(self.screens)

        if self.user_name:
            self._set_greeting()
            profile = self.settings.get("profile")
            last_screen = profile.get("current_screen", "calculator")
            self.screens.current = last_screen if last_screen in self.screens.screen_names else "calculator"
        else:
            self.greeting.text = "Welcome!"
            self.main_nav.height = 0
            self.main_nav.opacity = 0
            self.main_nav.disabled = True
            self.screens.current = "name_setup"

        Clock.schedule_once(self._apply_system_bars, .5)
        return root

    def _converter_screen_name(self, converter_name):
        return "detail_" + converter_name.lower().replace(" ", "_")

    def _set_greeting(self):
        self.greeting.text = f"[b]Hello, {escape_markup(self.user_name)}.[/b]"

    def _persist_current_screen(self, _manager, screen_name):
        if self.user_name and hasattr(self, "settings"):
            self.settings.put("profile", name=self.user_name, current_screen=screen_name)

    def _apply_system_bars(self, _dt):
        # Android 15+ draws edge-to-edge by default; pad the app below the
        # status bar and above navigation controls when p4a provides this API.
        try:
            from android.display_cutout import update_system_ui
            update_system_ui("#0b101b", "#0b101b", "Light", True, True)
        except (ImportError, RuntimeError, AttributeError):
            pass

    def on_pause(self):
        self._persist_current_screen(self.screens, self.screens.current)
        return True

    def on_resume(self):
        Clock.schedule_once(self._apply_system_bars, .2)

    def start_with_name(self):
        setup = self.screens.get_screen("name_setup")
        name = setup.name_input.text.strip()
        if not name:
            setup.error.text = "Please enter your name to continue."
            return
        self.user_name = name[:24]
        self.settings.put("profile", name=self.user_name, current_screen="calculator")
        self._set_greeting()
        self.main_nav.height = dp(56)
        self.main_nav.opacity = 1
        self.main_nav.disabled = False
        self.calculator_tab.selected = True
        self.converter_tab.selected = False
        self.screens.transition.direction = "left"
        self.screens.current = "calculator"

    def show_tab(self, tab):
        is_calculator = tab == "Calculator"
        self.calculator_tab.selected = is_calculator
        self.converter_tab.selected = not is_calculator
        if self.screens.current != ("calculator" if is_calculator else "converter_grid"):
            self.screens.transition.direction = "right" if is_calculator else "left"
            self.screens.current = "calculator" if is_calculator else "converter_grid"

    def open_converter(self, converter_name):
        screen_name = self.converter_screens[converter_name]
        self.converter_tab.selected = True
        self.calculator_tab.selected = False
        self.screens.transition.direction = "left"
        self.screens.current = screen_name

    def back_to_converters(self):
        self.screens.transition.direction = "right"
        self.screens.current = "converter_grid"


if __name__ == "__main__":
    EverydayCalculatorApp().run()

