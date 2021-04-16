It parses math through AST. What else do you want from me?

Here's an example

```python
import asyncio
import mathparser

expr = input("enter your equation: ")

lex = mathparser.MathLexer()
parser = mathparser.Parser(expr, lex)

async def main():
    try:
        tokens = list(lex.tokenize(expr))
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