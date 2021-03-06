import re
import math
import copy
import logging
from typing import List, Union, Callable, Any, Optional
from sly.lex import Token
from .lex import ArgLexer
from .errors import *

FUNCTION_RE = re.compile(r"([a-zA-Z]+)\(([a-zA-Z,\s]*)\)\s*=\s*(.*)") # P(x) = expr
PLOT_FUNCTION_RE = re.compile(r"y\s*=\s*(.*)")
SEQUENCE_RE = re.compile(r"[sS]\s*=\s*([^,\n]*),([^,\n]*),?([^,\n]*)?")
FUNCTIONCALL_RE = re.compile(r"([a-zA-Z]+)\s*\((.*)\)") # P(x[, y,...])
SEQUENCE_X_RE = re.compile(r"[sS]\s*[?!]!?\s*\((.*)\)") # s?|!|!!(400)

MAX_ALLOWABLE_NUMBER = 99999999
MAX_EXPONENT = 50

logger = logging.getLogger("mathparser")

class Builtins:
    def __init__(self):
        _num = ["num"]
        _num2 = ["num", "num2"]
        def _unwrap(func: Callable):
            def call(_, **kwargs):
                return func(*kwargs.values())

            return call
        self.builtins = {
            "rad": BuiltinFunction("rad", _num, _unwrap(math.radians)),
            "sin": BuiltinFunction("sin", _num, _unwrap(math.sin)),
            "cos": BuiltinFunction("cos", _num, _unwrap(math.cos)),
            "tan": BuiltinFunction("tan", _num, _unwrap(math.tan)),
            "asin": BuiltinFunction("asin", _num2, _unwrap(lambda x, y: math.asin(x/y))),
            "acos": BuiltinFunction("acos", _num2, _unwrap(lambda x, y: math.acos(x/y))),
            "atan": BuiltinFunction("atan", _num2, _unwrap(lambda x, y: math.atan(x/y))),
            "log": BuiltinFunction("log", _num, _unwrap(math.log)),
            "π": math.pi,
            "pi": math.pi,
            "E": math.e,
        }

class Parser:
    def __init__(self, user_input, lex):
        self.input = user_input
        self.lex = lex
        self.state = BUILTINS.builtins.copy()
        self.tokens: Optional[List[Token]] = None
        self.sequence: Optional["GeoSequence"] = None

    def parse(self, tokens: List[Token]):
        self.tokens = tokens
        expr = self.traverse_tokens(allow_functions=True)
        return expr

    def traverse_tokens(self, tokens: List[Token]=None, allow_functions=True):
        exprs = [Expression()]
        functioncalls = []
        bracket = None
        depth = 0
        tokens = tokens or self.tokens
        last_token = None
        skip = 0

        for index, token in enumerate(tokens):
            if skip:
                skip -= 1
                continue

            if token.type in ("NUMBER", "NAME"):
                last_token = token
                if bracket:
                    bracket.add_chunk(token)
                else:
                    exprs[-1].add_chunk(token)

                continue

            elif token.type == "OPERATOR":
                if not last_token and token.value != "-":
                    raise TokenizedUserInputError(self.input, token, "Unexpected operator")

                if last_token and last_token.type == "OPERATOR":
                    raise TokenizedUserInputError(self.input, token, "Unexpected operator")

                if token.value == "-" and last_token and last_token.value == "-":
                    _token = copy.copy(token)
                    _token.value = "+"
                    if bracket:
                        bracket.tokens.pop()
                        bracket.tokens.append(Operator(_token))
                    else:
                        exprs[-1].chunks.pop()
                        exprs[-1].chunks.append(Operator(_token))

                    last_token = token
                    continue

                elif last_token and last_token.value == token.value:
                    raise TokenizedUserInputError(self.input, token, f"Unexpected '{token.value}'")

                token = Operator(token)
                last_token = token
                if bracket:
                    bracket.add_chunk(token)
                else:
                    exprs[-1].add_chunk(token)

                continue

            elif token.type == "(":
                depth += 1
                if depth == 1:
                    last_token = token
                    bracket = Bracket(token)
                    continue

            elif token.type == ")":
                depth -= 1
                if depth == 0:
                    last_token = token
                    exprs[-1].add_chunk(bracket)
                    bracket = None
                    continue

                if depth < 0:
                    raise TokenizedUserInputError(self.input, token, "Unexpected closing bracket")

            elif token.type == "FUNCTION":
                if not allow_functions:
                    raise TokenizedUserInputError(self.input, token, "Functions are not allowed here")

                groups = FUNCTION_RE.match(token.value)
                name, args, value = groups.groups()
                f = Function(name, args, self.traverse_tokens(
                    list(self.lex.tokenize(
                        value, #lineno=token.lineno, index=token.index+offset
                    )), allow_functions=False)[0].chunks
                )

                self.state[f.name] = f
                last_token = f
                try:
                    if tokens[index+1].type == "NEWLINE":
                        skip += 1
                except IndexError:
                    pass

                continue

            elif token.type == "NEWLINE":
                exprs.append(Expression())
                continue

            elif token.type == "FUNCTION_CALL":
                toks = FUNCTIONCALL_RE.match(token.value)
                name, args = toks.groups()
                args = self.parse_args(token, token.value.find("("), args)
                f = FunctionCall(token, name, args)
                last_token = f
                exprs[-1].add_chunk(f)
                functioncalls.append(f)
                continue

            elif token.type in ("SEQUENCE_N_CALL", "SEQUENCE_S_CALL", "SEQUENCE_SN_CALL"):
                toks = SEQUENCE_X_RE.match(token.value)
                args = toks.groups()[0]
                args = self.parse_args(token, token.value.find("("), args)
                f = FunctionCall(token, "s", args)
                last_token = f
                exprs[-1].add_chunk(f)
                functioncalls.append(f)
                continue

            elif token.type == "PLOT_FUNCTION":
                if not allow_functions:
                    raise TokenizedUserInputError(self.input, token, "Functions are not allowed here")

                groups = PLOT_FUNCTION_RE.match(token.value)
                value = groups.groups()[0]
                f = PlottableFunction("y", ["x"], self.traverse_tokens(list(self.lex.tokenize(value)), allow_functions=False)[0].chunks)

                exprs.append(f)
                last_token = f
                try:
                    if tokens[index+1].type == "NEWLINE":
                        skip += 1
                except IndexError:
                    pass

                continue

            elif token.type == "SEQUENCE":
                if not allow_functions:
                    raise TokenizedUserInputError(self.input, token, "Sequences are not allowed here")

                if "S" in self.state:
                    raise TokenizedUserInputError(self.input, token, "A sequence has already been defined")

                groups = SEQUENCE_RE.match(token.value)
                attrs = list(groups.groups())
                self.sequence = seq = GeoSequence(token, attrs)
                fn = SequenceFunction(seq)
                self.state['S'] = self.state['s'] = fn
                continue

            else:
                raise ValueError(f"Unexpected token {token!r}")

        for call in functioncalls:
            call.validate(self)

        if allow_functions:
            if self.sequence:
                self.sequence.validate(self)

            for x in self.state.values():
                try:
                    x.validate(self)
                except AttributeError:
                    pass

        for expr in exprs.copy():
            expr.validate(self)
            if not expr.chunks:
                exprs.remove(expr)

        return exprs

    def parse_args(self, _, __, args: str):
        tokens = list(ArgLexer().tokenize(args))
        v = self.traverse_tokens(tokens, allow_functions=False)
        args = [x for x in v if (isinstance(x, Token) and x.type != ",") or not isinstance(x, Token)]
        return args

    def get_var_with_state(self, var: Token, namespace: dict=None):
        if namespace and var.value in namespace:
            return namespace[var.value]

        if var.value in self.state.keys():
            v = self.state[var.value]
            if isinstance(v, (int, float)):
                return v

        raise TokenizedUserInputError(self.input, var, f"Variable '{var.value}' does not exist")

    def get_var(self, var: str, namespace: dict=None):
        if namespace and var in namespace:
            return namespace[var]
        elif var in self.state:
            return self.state[var]

        raise UserInputError(f"Variable '{var}' does not exist")

    def _quick_call(self, seq: List[Union["Bracket", Token, "Operator", "FunctionCall"]], namespace: dict):
        v = seq[-1]
        if isinstance(v, (int, float)):
            return v
        elif isinstance(v, str):
            return self.get_var(v, namespace)
        elif isinstance(v, Token):
            if v.type == "NUMBER":
                return v.value

            return self.get_var_with_state(v, namespace)
        elif isinstance(v, (FunctionCall, Bracket)):
            return v.execute(self, namespace)

        raise RuntimeError(f"unable to determine types. {v!r}")

    def do_math(self, seq: List[Union["Bracket", Token, "Operator", "FunctionCall"]], namespace: dict):
        logger.debug("----START-----")
        logger.debug(namespace, seq)
        if len(seq) < 3:
            logger.debug("----QUICKCALL-END----")
            return self._quick_call(seq, namespace)

        ops = _ops = []
        # loop one, solve brackets/function calls, abstract down to numbers
        for i in seq:
            if isinstance(i, Bracket):
                ops.append(self.do_math(i.tokens, namespace))
            elif isinstance(i, FunctionCall):
                ops.append(i.execute(self, namespace))
            elif isinstance(i, Token):
                ops.append(i.value)
            else:
                ops.append(i)

        # loop through for each operator to apply bedmas
        logger.debug(ops)
        for operator in ("^", "/", "*", "+", "-"):
            it = iter(enumerate(ops))
            new = []
            for i, left in it:
                if isinstance(left, Operator):
                    if left.op == operator:
                        op = left
                        left = new.pop()
                    else:
                        logger.debug(i, left, new, ops, _ops)
                        new.append(left)
                        continue
                else:
                    try:
                        _, op = next(it)
                    except StopIteration:
                        if isinstance(left, str):  # variable
                            left = self.get_var(left, namespace)

                        new.append(left)
                        continue

                    assert isinstance(op, Operator), AssertionError(left, op, new, ops, _ops)
                    if op.op != operator:
                        new.append(left)
                        new.append(op)
                        continue

                _, right = next(it)
                if isinstance(right, str): #variable
                    right = self.get_var(right, namespace)

                if isinstance(left, str): #variable
                    left = self.get_var(left, namespace)

                logger.debug(left, right)
                value = op.execute(self, left, right)
                new.append(value)

            logger.debug(new, ops)
            ops = new
            if len(ops) == 1:
                break

        logger.debug(ops)
        logger.debug("----END----")
        return ops[0]


class Operator:
    __slots__ = "op", "token"
    value = None
    type = None
    OPS = {
        "+": lambda l, r: l + r,
        "-": lambda l, r: l - r,
        "*": lambda l, r: l * r,
        "/": lambda l, r: l / r,
        "^": lambda l, r: math.pow(l, r),
    }
    def __init__(self, token: Token):
        self.op = token.value
        self.token = token

    def __repr__(self):
        return f"<Operator {self.op}>"

    def execute(self, parser: Parser, left: Union[int, float], right: Union[int, float]):
        if left > MAX_ALLOWABLE_NUMBER:
            raise EvaluationError(parser.tokens, self.token, left, right,
                                  "Number (left) is larger than the permissible values")
        if right > MAX_ALLOWABLE_NUMBER:
            raise EvaluationError(parser.tokens, self.token, left, right,
                                  "Number (right) is larger than the permissible values")
        if self.op == "^" and right > MAX_EXPONENT:
            raise EvaluationError(parser.tokens, self.token, left, right,
                                  "Number (right) is larger than the permissible values")
        return self.OPS[self.op](left, right)

class Expression:
    __slots__ = "chunks",
    value = None
    type = None
    plot = False

    def __init__(self):
        self.chunks = [] # type: List[Union[Bracket, Token, Operator, FunctionCall]]

    def add_chunk(self, obj: Union["Bracket", Token, Operator, "FunctionCall"]):
        if self.chunks:
            if isinstance(obj, Token) and obj.type in ("NUMBER", "NAME"):
                t = Token()
                t.value = "*"
                t.index = obj.index
                t.lineno = obj.lineno
                t.type = "OPERATOR"
                if isinstance(self.chunks[-1], Token) and self.chunks[-1].type in ("NUMBER", "NAME"):
                    self.chunks.append(Operator(t))

                elif isinstance(self.chunks[-1], Bracket):
                    self.chunks.append(Operator(t))

            elif isinstance(obj, Bracket):
                if isinstance(self.chunks[-1], Token) and self.chunks[-1].type in ("NUMBER", "NAME"):
                    t = Token()
                    t.value = "*"
                    t.index = obj.start.index
                    t.lineno = obj.start.lineno
                    t.type = "OPERATOR"
                    self.chunks.append(Operator(t))

        self.chunks.append(obj)

    def validate(self, _: Parser):
        def _t(t0, t1, x):
            if isinstance(t0, Operator) and t0.op == "-" and isinstance(t1, Token) and t1.type == "NUMBER":
                t1.value *= -1
                t1.index -= t1.index - t0.token.index
                x[0] = t1
                del x[1]

        if len(self.chunks) > 1:
            t0_ = self.chunks[0]
            t1_ = self.chunks[1]
            _t(t0_, t1_, self.chunks)

        if self.chunks and isinstance(self.chunks[0], Bracket) and len(self.chunks[0].tokens)>1:
            t0_ = self.chunks[0].tokens[0]
            t1_ = self.chunks[0].tokens[1]
            _t(t0_, t1_, self.chunks[0].tokens)

    def execute(self, _: Any, parser: Parser, namespace: dict=None):
        return parser.do_math(self.chunks, namespace)

    def __repr__(self):
        return f"<Expression {self.chunks}>"


class Bracket:
    __slots__ = "tokens", "start"
    value = None
    type = None

    def __init__(self, start: Token):
        self.tokens = []
        self.start = start

    def add_chunk(self, obj: Union["Bracket", Token, Operator, "FunctionCall"]):
        if self.tokens:
            if isinstance(obj, Token) and obj.type in ("NUMBER", "NAME"):
                t = Token()
                t.value = "*"
                t.index = obj.index
                t.lineno = obj.lineno
                t.type = "OPERATOR"
                if isinstance(self.tokens[-1], Token) and self.tokens[-1].type in ("NUMBER", "NAME"):
                    self.tokens.append(Operator(t))

                elif isinstance(self.tokens[-1], Bracket):
                    self.tokens.append(Operator(t))

            elif isinstance(obj, Bracket):
                if isinstance(self.tokens[-1], Token) and self.tokens[-1].type in ("NUMBER", "NAME"):
                    t = Token()
                    t.value = "*"
                    t.index = obj.start.index
                    t.lineno = obj.start.lineno
                    t.type = "OPERATOR"
                    self.tokens.append(Operator(t))

        self.tokens.append(obj)

    def execute(self, parser: Parser, namespace: dict=None):
        expr = parser.traverse_tokens(self.tokens, allow_functions=False)
        if len(expr) > 1:
            raise TokenizedUserInputError(parser.input, self.start, "Invalid Syntax (multi-expr)")
        expr = expr[0]

        return parser.do_math(expr.chunks, namespace)

    def __repr__(self):
        return f"<Bracket {self.tokens}>"

class GeoSequence:
    __slots__ = "values", "geometric", "t", "d", "token"
    value = None

    def __init__(self, token: Token, values: List[str]):
        self.values = values
        self.token = token
        self.geometric: bool = None # noqa
        self.t: float = None # noqa
        self.d: float = None # noqa

    def validate(self, parser: Parser):
        if len(self.values) < 2:
            raise TokenizedUserInputError(parser.input, self.token, f"Expected 2-3 sequence values, got {len(self.values)}")

        arg1 = parser.parse_args(None, None, self.values[0])[0].execute(None, parser)
        if int(arg1) == arg1:
            arg1 = int(arg1)

        arg2 = parser.parse_args(None, None, self.values[1])[0].execute(None, parser)
        if int(arg2) == arg2:
            arg2 = int(arg2)

        arg3 = None

        if self.values[2]:
            arg3 = parser.parse_args(None, None, self.values[2])[0].execute(None, parser)
            if int(arg3) == arg3:
                arg3 = int(arg3)

        self.t = arg1
        self.d = arg2 / arg1

        if arg3 and arg3 / arg2 != self.d:
            raise TokenizedUserInputError(
                parser.input,
                self.token,
                f"Invalid sequence ({arg2}/{arg1} != {arg3}/{arg2})"
            )

    def execute(self, token: Token, parser: Parser, value: Union[int, float]) -> Union[int, float]:
        if token.type not in self._EXECUTIONS:
            raise TokenizedUserInputError(parser.input, token, "Unknown sequence operation")

        return self._EXECUTIONS[token.type](self, token, parser, value) # noqa

    def _execute_n_tn(self, token: Token, parser: Parser, value: Union[int, float]) -> Union[int, float]:
        if value > MAX_EXPONENT:
            raise TokenizedUserInputError(
                parser.input,
                token,
                f"Exponents are restricted to {MAX_EXPONENT} (got {value})"
            )

        return self.t * (self.d ** (value - 1))

    def _execute_tn_n(self, _: Token, __: Parser, value: Union[int, float]) -> Union[int, float]:
        return (math.log(value / self.t) / math.log(self.d)) + 1

    def _execute_n_sm(self, token: Token, parser: Parser, value: Union[int, float]) -> Union[int, float]:
        if value > MAX_EXPONENT:
            raise TokenizedUserInputError(
                parser.input,
                token,
                f"Exponents are restricted to {MAX_EXPONENT} (got {value})"
            )

        return (self.t * ((self.d ** value) - 1)) / (self.d - 1)

    def _execute_tn_sm(self, _: Token, __: Parser, value: Union[int, float]) -> Union[int, float]:
        return (self.d*value-self.t)/(self.d-1)

    _EXECUTIONS = {
        "FUNCTION_CALL": _execute_n_tn,
        "SEQUENCE_N_CALL": _execute_tn_n,
        "SEQUENCE_S_CALL": _execute_n_sm,
        "SEQUENCE_SN_CALL": _execute_tn_sm
    }

class Function:
    __slots__ = "name", "args", "chunks"
    value = None
    plot = False

    def __init__(self, name: str, args: List[str], chunks: List[Union[Bracket, Token, Operator]]):
        self.name = name
        self.args = args
        self.chunks = chunks

    def validate(self, parser: Parser):
        def validate_chunk(_chunk):
            if isinstance(_chunk, Bracket):
                for c in _chunk.tokens:
                    validate_chunk(c)

            elif isinstance(_chunk, Token):
                if _chunk.type == "NAME":
                    if _chunk.value not in self.args and _chunk.value not in parser.state:
                        raise TokenizedUserInputError(parser.input, _chunk, f"Unknown variable: '{_chunk.value}'")

        for chunk in self.chunks:
            validate_chunk(chunk)

    def plots(self, parser: Parser):
        """
        Returns a dict of x:y coordinates
        """
        scope = {"x": 0}
        plots = {}

        for x in range(-5, 6):
            scope['x'] = x
            try:
                y = parser.do_math(self.chunks, scope)
            except ZeroDivisionError:
                y = None
            plots[x] = y

        return plots

    def execute(self, _: Token, parser: Parser, scope: dict=None):
        return parser.do_math(self.chunks, scope)

    def __repr__(self):
        return f"<Function name={self.name} args={self.args} chunks={self.chunks}"

class PlottableFunction(Function):
    plot = True

    def execute(self, _: Token, parser: Parser, scope: dict=None):
        return self.plots(parser)

class SequenceFunction(Function):
    __slots__ = "sequence",

    def __init__(self, sequence: GeoSequence): # noqa
        self.name = "S"
        self.args = ["value"]
        self.chunks = None
        self.sequence = sequence

    def validate(self, parser: Parser):
        pass

    def execute(self, token: Token, parser: Parser, scope: dict=None):
        if not scope:
            raise ValueError("shouldnt get here")

        return self.sequence.execute(token, parser, scope['value'])

class BuiltinFunction(Function):
    def __init__(self, name: str, args: List[str], callback: Callable): # noqa
        self.name = name
        self.args = args
        self.chunks = callback

    def validate(self, parser: Parser):
        pass

    def execute(self, token: Token, parser: Parser, scope: dict=None):
        try:
            return self.chunks(parser, **scope)
        except ZeroDivisionError:
            raise TokenizedUserInputError(parser.input, token, "Division by 0")

    def __repr__(self):
        return f"<BuiltinFunction name={self.name} args={self.args}>"


class FunctionCall:
    __slots__ = "_start", "name", "args"
    value = None
    type = None

    def __init__(self, t: Token, name: str, tokens: List[Union[Expression, "FunctionCall", Token]]):
        self._start = t
        self.name = name
        self.args = tokens

    def validate(self, parser: Parser, scope: dict=None):
        if self.name not in parser.state:
            raise TokenizedUserInputError(parser.input, self._start, f"Function '{self.name}' not found")

        func = parser.state[self.name]

        if len(func.args) != len(self.args):
            logger.debug(str((self.args, func.args)))
            raise TokenizedUserInputError(
                parser.input,
                self._start,
                f"{'Not enough' if len(func.args)>len(self.args) else 'Too many'} arguments passed to {self.name}"
            )

        for arg in self.args:
            if isinstance(arg, (str, int)):
                if not scope and arg not in parser.state:
                    raise TokenizedUserInputError(parser.input, self._start, f"Variable '{arg}' not found")

                elif scope and arg not in scope and arg not in parser.state:
                    raise TokenizedUserInputError(parser.input, self._start, f"Variable '{arg}' not found")

            elif isinstance(arg, FunctionCall):
                arg.validate(parser, scope)

    def execute(self, parser: Parser, scope: dict=None):
        func = parser.state[self.name] # it should already be there, we validated earlier
        if not isinstance(func, Function):
            raise ValueError("function expected. todo: this errror") # TODO

        args = {}
        for index, arg in enumerate(self.args):
            if isinstance(arg, Expression):
                args[func.args[index]] = parser.do_math(arg.chunks, scope)
            else:
                try:
                    args[func.args[index]] = arg.execute(parser, scope)
                except AttributeError:
                    if arg.type == "NAME":
                        args[func.args[index]] = parser.get_var_with_state(arg, scope)
                    else:
                        args[func.args[index]] = arg.value

        return func.execute(self._start, parser, args)

BUILTINS = Builtins()
