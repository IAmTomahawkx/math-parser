___
# Math Parser
___
It parses math through AST.

## Index
- [Example](#python-example)
- [Complexities](#complexities)
- [Built-ins](#built-ins)

## Python Example

```python
import asyncio
import mathparser

exp = input("enter your equation: ")

lex = mathparser.MathLexer()
parser = mathparser.Parser(expr, lex)

async def main():
    try:
        tokens = list(lex.tokenize(exp))
        exprs = parser.parse(tokens)
        resp = ""
        images = []
        
        for i, expr in enumerate(exprs):
            try:
                e = expr.execute(None, parser)
            except ZeroDivisionError: # this one is intentionally left unhandled
                resp += f"[{i+1}] Zero divison error"
                continue
            
            if isinstance(e, dict):
                f = await mathparser.graph.plot(e, i+1)
                if f:
                    images.append(f)
    
                resp += f"[{i+1}] See graph {i+1} ({e})\n"
            else:
                resp += f"[{i+1}] {e}\n"
        
        print(resp)
        # do something with the images
    except mathparser.UserInputError as e:
        print(str(e)) # userinputerrors have formatted errors attached to them
        raise

asyncio.run(main())
```

## Complexities
This parser handles more than just the obvious addition, subtraction, multiplication and division.
Here is a list of more complex things this can do currently.

- [brackets](#brackets)
- [exponents](#exponents)
- [functions](#functions)
- [graphed functions](#graphed-functions)
- [geometric sequences](#geometric-sequences)

___

### Brackets
Brackets are fairly simple, but it's worth mentioning that `2+4*5` (22) will be calculated differently than `(2+4)*5` (30).
___

### Exponents
Again, nothing crazy here, exponents can be indicated with the `^` symbol. Ex. `2^2`
___

### Functions
Functions are created with the syntax 
```
p(x) = ...
```
p can be whatever letter you wish, except `s`/`S` (these are reserved for sequences).
The `...` represents where your expression should go. \
A function with multiple variables can be created in the same way:
```
p(x,y)=...`. Ex. `p(x,y)=x*5+y-4
```

Functions can be called in the following manner
```
p(...)
```
This can be anywhere, excluding the function itself. Ex.
```
p(x) = x*4
p(4)+5
```
will result in 21.
___

### Graphed Functions
Graphed functions are similar to normal functions, but with two major differences. \
The first difference is that graphed functions cannot be called from your expressions. \
The second difference is that graphed functions are declared using `y=...`, instead of `p(x)=...`.
The `x` variable is implicitly injected as it's graphed.
___

### Geometric Sequences
Geometric sequences are defined with the following syntax
```
s=n1,n2,n3
```
or
```
s=n1,n2
```
where `s` is a literal `s`, `n1` is the first value in the sequence, `n2` is the second value, and optionally, `n3` is the third value. \
When a sequence is defined, you can use the following syntaxes
```
S(...)
S?(...)
S!(...)
S!!(...)
```

Here's what each one does:
`S(...)`: takes 1 number, `n`, and returns its value in the sequence. Ex.
```
S=2,4,8
s(2)
```
`s(2)` will be 4, `s(3)` will be 8, and so on.

`S?(...)`: takes 1 number, `tn`, and returns its position in the sequence. Ex.
```
S=2,4,8
s?(4)
```
`s?(4)` will be 2, `s?(8)` will be 3, and so on.

`S!(...)`: takes 1 number, `n`, and returns the sum of the sequence up to that position. Ex.
```
S=2,4,8
s!(3)
```
`s!(3)` will be 14, `s!(4)` will be 30, and so on.

`S!!(...)`: takes 1 number, `tn`, and returns the sum of the sequence up to that value. Ex.
```
S=2,4,8
s!!(8)
```
`s!!(8)` will be 14, `s!!(16)` will be 30.


## Built-ins
The following functions are currently built into the parser
- sin(x) / asin(x, y)
- cos(x) / acos(x, y)
- tan(x) / atan(x, y)
- log(n)

The following variables are currently built in to the parser
- pi
- E