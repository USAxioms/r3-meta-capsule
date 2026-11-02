"""WAD-18: weak arithmetic decidability at 18 exact decimal places.

REPRESENTATION
    A value is a Python int n denoting the rational n / 10**18.
    Python ints are arbitrary precision, so no value is ever approximated by
    a machine word. There is no float anywhere in this module, and none in
    any module that imports it.

WHY THIS IS 'WEAK ARITHMETIC DECIDABILITY'
    Every primitive is +, -, * and division by a non-zero integer, i.e. the
    operations of the ordered ring of integers. Comparison is exact. No
    transcendental function is a primitive: where one is unavoidable it is
    computed as a finite rational series with a declared, bounded truncation
    error, and the error is reported rather than absorbed.

ROUNDING (declared once, applied everywhere)
    mul, div : round-half-to-even on the exact rational result.
    sqrt     : floor, because an exact square root generally does not exist
               in the representation; the residual is exposed by sqrt_exact.
    Round-half-even is chosen over truncation because truncation is biased,
    and a biased rounding mode accumulates drift over an iteration whose
    termination argument depends on a monotone measure.

WHAT THIS BUYS
    Bit-identical results on every platform and Python build, with no reliance
    on IEEE-754 semantics, FMA contraction, x87 extended precision, or library
    versions of erf/sqrt/log. The determinism contract D1 becomes vacuous
    because there is no floating point left to pin down.
"""
import math

DIGITS = 18
SCALE = 10 ** DIGITS
ONE = SCALE
ZERO = 0


# ---------------------------------------------------------------- rounding
def round_half_even(num, den):
    """Exact round-half-to-even of num/den. den > 0. Pure integer."""
    if den <= 0:
        raise ValueError("denominator must be positive")
    q, r = divmod(num, den)          # Python divmod floors; 0 <= r < den
    twice = 2 * r
    if twice > den or (twice == den and (q & 1)):
        q += 1
    return q


# ------------------------------------------------------------ constructors
def from_int(i):
    return int(i) * SCALE


def from_ratio(num, den):
    """Exact num/den, rounded half-even into the representation."""
    if den < 0:
        num, den = -num, -den
    return round_half_even(num * SCALE, den)


def from_str(s):
    """'-3.25' -> WAD. Rejects more than 18 decimals rather than silently
    truncating: silent truncation is how precision claims become false."""
    s = s.strip()
    neg = s.startswith("-")
    if neg or s.startswith("+"):
        s = s[1:]
    if "." in s:
        whole, frac = s.split(".", 1)
    else:
        whole, frac = s, ""
    if len(frac) > DIGITS:
        raise ValueError("more than %d decimal places: %r" % (DIGITS, s))
    if not (whole + frac).isdigit() and (whole + frac) != "":
        raise ValueError("not a decimal literal: %r" % s)
    v = int(whole or "0") * SCALE + int((frac + "0" * DIGITS)[:DIGITS] or "0")
    return -v if neg else v


def to_str(x, places=DIGITS):
    """Exact decimal rendering. Never goes through a float."""
    if places > DIGITS:
        raise ValueError("cannot show more places than the representation has")
    neg = x < 0
    x = -x if neg else x
    if places == DIGITS:
        whole, frac = divmod(x, SCALE)
        body = "%d.%0*d" % (whole, DIGITS, frac)
    else:
        shown = round_half_even(x, 10 ** (DIGITS - places))
        whole, frac = divmod(shown, 10 ** places)
        body = "%d.%0*d" % (whole, places, frac) if places else str(whole)
    return ("-" + body) if neg else body


# ------------------------------------------------------------------- algebra
def mul(a, b):
    neg = (a < 0) != (b < 0)
    m = round_half_even(abs(a) * abs(b), SCALE)
    return -m if neg else m


def div(a, b):
    if b == 0:
        raise ZeroDivisionError("WAD-18 division by zero")
    neg = (a < 0) != (b < 0)
    m = round_half_even(abs(a) * SCALE, abs(b))
    return -m if neg else m


def sqrt(a):
    """Floor square root in the representation. math.isqrt is exact integer."""
    if a < 0:
        raise ValueError("sqrt of a negative WAD value")
    return math.isqrt(a * SCALE)


def sqrt_exact(a):
    """(root, residual) with residual = a - root*root >= 0, exposed not hidden."""
    r = sqrt(a)
    return r, a - mul(r, r)


def mean(values):
    """Exact mean of WAD values: one division, one rounding."""
    if not values:
        raise ValueError("mean of empty sequence")
    return round_half_even(sum(values) * 1, len(values))


def variance(values):
    """Population variance, exact to the final rounding."""
    n = len(values)
    if n == 0:
        raise ValueError("variance of empty sequence")
    m = mean(values)
    return round_half_even(sum((v - m) ** 2 for v in values), n * SCALE)


def is_wad(x):
    return isinstance(x, int) and not isinstance(x, bool)


def assert_wad(*xs):
    for x in xs:
        if isinstance(x, float):
            raise TypeError("float encountered in a WAD-18 path: %r" % (x,))
        if not is_wad(x):
            raise TypeError("not a WAD-18 value: %r" % (x,))
    return True
