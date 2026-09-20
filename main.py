from decimal import Decimal, InvalidOperation, getcontext
from pathlib import Path
import json
import math
import os
import re

from flask import Flask, jsonify, render_template, request


app = Flask(__name__)

BASE_DIR = Path(__file__).parent
LANG_DIR = BASE_DIR / "languages"
MAX_NUMBER_LENGTH = 5000


def parse_number(text):
    text = text.strip().replace(" ", "").replace(",", ".")
    if not text:
        return None

    if "i" not in text.lower():
        try:
            return complex(Decimal(text), 0)
        except InvalidOperation:
            return None

    text = text.replace("I", "i")

    if text in ("i", "+i"):
        return complex(0, 1)
    if text == "-i":
        return complex(0, -1)

    pattern = (
        r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))?"
        r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))i"
    )
    match = re.fullmatch(pattern, text)

    if not match:
        return None

    try:
        real = Decimal(match.group(1) or "0")
        imaginary = Decimal(match.group(2) or "1")
    except InvalidOperation:
        return None

    return complex(real, imaginary)


def precision_value(text, default=None):
    if not text:
        return default

    try:
        value = int(text)
    except ValueError:
        return None

    if not 0 <= value <= 100:
        return -1

    return value


def root_decimal(number, degree, precision):
    getcontext().prec = precision + 20

    if number == 0:
        return Decimal(0)

    negative = number < 0
    number = abs(number)
    guess = (number.ln() / degree).exp()
    tolerance = Decimal(10) ** -(precision + 5)

    for _ in range(precision * 4 + 50):
        previous = guess
        guess = (
            (degree - 1) * guess + number / guess ** (degree - 1)
        ) / degree

        if abs(guess - previous) < tolerance:
            break

    return -guess if negative else guess


def decimal_text(number, precision=None):
    if number == number.to_integral_value():
        return str(number.quantize(Decimal(1)))

    if precision is None:
        raise ValueError("precision_required")

    return f"{number:.{precision}f}"


def complex_roots(number, degree):
    radius = abs(number) ** (1 / degree)
    angle = math.atan2(number.imag, number.real)

    return [
        complex(
            radius * math.cos((angle + 2 * math.pi * k) / degree),
            radius * math.sin((angle + 2 * math.pi * k) / degree),
        )
        for k in range(degree)
    ]


def complex_text(number, precision):
    epsilon = 10 ** -(precision + 1)
    real = 0 if abs(number.real) < epsilon else number.real
    imaginary = 0 if abs(number.imag) < epsilon else number.imag

    def format_number(value):
        return f"{value:.{precision}f}".rstrip("0").rstrip(".") or "0"

    if imaginary == 0:
        return format_number(real)

    if real == 0:
        if abs(imaginary - 1) < epsilon:
            return "i"
        if abs(imaginary + 1) < epsilon:
            return "-i"
        return format_number(imaginary) + "i"

    sign = "+" if imaginary > 0 else "-"
    value = format_number(abs(imaginary))

    if value == "1":
        value = ""

    return f"{format_number(real)} {sign} {value}i"


def language_list():
    return sorted(path.stem for path in LANG_DIR.glob("*.json"))


def language_data(code):
    path = LANG_DIR / f"{code}.json"

    if not path.exists():
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def error(message):
    return {"ok": False, "error": message}


def get_precision(text, default=None):
    precision = precision_value(text, default)

    if precision == -1:
        return None, error("precision_range")
    if precision is None:
        return None, error("precision_integer")

    return precision, None


def complex_response(number, degree, precision, analytical, number_text, prefix):
    roots = [complex_text(root, precision) for root in complex_roots(number, degree)]

    return jsonify({
        "ok": True,
        "type": "complex",
        "roots": roots,
        "analytical": f"{prefix}^{degree} = {number_text}" if analytical else None,
    })


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/languages")
def languages():
    return jsonify(language_list())


@app.get("/language/<code>")
def language(code):
    data = language_data(code)

    if data is None:
        return jsonify(error("language_not_found")), 404

    return jsonify(data)


@app.post("/calculate")
def calculate():
    data = request.get_json(silent=True) or {}

    number_text = str(data.get("number", "")).strip()
    degree_text = str(data.get("degree", "")).strip()
    precision_text = str(data.get("precision", "")).strip()
    complex_mode = bool(data.get("complex_mode", True))
    analytical = bool(data.get("analytical", False))

    if not number_text:
        return error("number_required")
    if not degree_text:
        return error("degree_required")
    if len(number_text) > MAX_NUMBER_LENGTH:
        return error("number_too_large")

    number = parse_number(number_text)
    if number is None:
        return error("not_number")

    try:
        degree = int(degree_text)
    except ValueError:
        return error("degree_integer")

    if degree <= 0:
        return error("degree_positive")
    if degree > 1000:
        return error("degree_too_large")

    # Комплексное число: сразу возвращаем все комплексные корни.
    if number.imag != 0:
        precision, response = get_precision(precision_text, 6)
        if response:
            return response

        return complex_response(
            number, degree, precision, analytical, number_text, "z"
        )

    number = Decimal(str(number.real))

    if number == 0:
        return jsonify({
            "ok": True,
            "type": "zero",
            "roots": ["0"],
            "analytical": "x = 0" if analytical else None,
        })

    # Четная степень отрицательного числа имеет комплексные корни.
    if number < 0 and degree % 2 == 0:
        if not complex_mode:
            return error("even_negative")

        precision, response = get_precision(precision_text, 6)
        if response:
            return response

        return complex_response(
            complex(float(number)),
            degree,
            precision,
            analytical,
            number_text,
            "x",
        )

    try:
        work_precision = max(120, abs(number).adjusted() + 50)
        root = root_decimal(number, degree, work_precision)

        if root == root.to_integral_value():
            result = decimal_text(root)
        else:
            if not precision_text:
                return error("precision_required")

            precision, response = get_precision(precision_text)
            if response:
                return response

            result = decimal_text(root_decimal(number, degree, precision), precision)

    except (InvalidOperation, OverflowError, ZeroDivisionError, ValueError):
        return error("calculation_error")

    roots = [f"+{result}", f"-{result}"] if number > 0 and degree % 2 == 0 else [result]

    return jsonify({
        "ok": True,
        "type": "real",
        "roots": roots,
        "analytical": f"x^{degree} = {number_text}" if analytical else None,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
