# Combinatorial Parsing in Python

Author: Darren M. Struthers - <dstruthers@gmail.com>

## Premise

The `parsing` library is a combinatorial parsing framework. As such, it provides
an extensible collection of atomic parsers, as well as combinators. These can be
used together to build up complex parsers from simple, understandable, building
blocks.

## Basic Overview

Individual Parsers are callable, and in most cases, there is no harm in thinking
of them merely as functions which receive input, attempt to parse it, and
return some output.

The simplest parser is `constant`. Initialize it with a value, and it will be
capable of consuming that value from the input, and nothing else.

```python
>>> from parsing import *
>>> my_parser = constant('foo')
>>> my_parser('foo')
'foo'
```

Attempting to feed the parser some other input will result in an exception.

```python
>>> my_parser('bar')
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/home/dstruthers/python-parsing/parsing.py", line 42, in __call__
    return self.parse(Input(input))
  File "/home/dstruthers/python-parsing/parsing.py", line 180, in parse
    raise mismatch(expected=repr(self.value), received=repr(input))
parsing.ParserError: Expected 'foo' but received 'bar'
```

Although, passing extra input won't cause a problem. When this happens,
the result object passed back by the parser will contain an extra
`remainder` property, showing the left-over input.

```python
>>> my_parser('food')
'foo'
>>> my_parser('food').remainder
'd'
```
Of course, if you want to guarantee no input is left over, you can use the `eof`
parser, which matches the end of the input stream.

```python
>>> my_parser = 'foo' + eof
>>> my_parser('food')
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/home/dstruthers/python-parsing/parsing.py", line 42, in __call__
    return self.parse(Input(input))
  File "/home/dstruthers/python-parsing/parsing.py", line 284, in parse
    result += parser(input)
  File "/home/dstruthers/python-parsing/parsing.py", line 40, in __call__
    return self.parse(input)
  File "/home/dstruthers/python-parsing/parsing.py", line 200, in parse
    raise mismatch(expected=self.desc, received=repr(input))
parsing.ParserError: Expected end of input but received 'd'
```
Whenever possible, this framework attempts to provide error messages that are
human readable, providing insight into the nature of the parsing error.

## Overloaded Operators

In the example above, we were able to create a parser as follows:

```python
my parser = 'foo' + eof
```

When used with the operators they support, `Parser` objects attempt to coerce
their neighboring operands to `Parser` instances as well, so in this case,
`'foo'` is implicitly cast to `constant('foo')`. When the `+` operator is used
on `Parser`s, the operands are combined into a `sequence`, which simply calls
its list of parsers on its input, in order.

Therefore, the parser above is equivalent to:

```python
my_parser = sequence([constant('foo'), eof])
```
Operators are often a useful way to make parser definitions much more succinct.
`*` can be used to repeat parsers.

```python
cats1 = constant('cat') * 10
cats2 = constant('catcatcatcatcatcatcatcatcatcat')

pets1 = one_of(['cat', 'dog']) * 3
pets2 = repeat(one_of(['cat', 'dog']), 3)
```
                  
`one_of` succeeds if one of the parsers in its list succeeds. The shorthand for
`one_of` is the `|` operator.

```python
pets3 = (constant('cat') | constant('dog')) * 3
```
Python's bitwise NOT operator, `~`, can also be used as an equivalent for the
`not_` combinator, which consumes one character of input as long as the
beginning of the input cannot be parsed by its argument.

```python
no_cat1 = ~constant('cat')
no_cat2 = not_('cat')
```

## `not_` vs. `until`

`not_` only consumes one character of input at a time because it is not
"greedy". The greedy equivalent of `not_` is `until`, which consumes as many
characters of input as it can before encountering a match for its parser.

```python
>>> i = 'aaaaaahh!!!'
>>> not_('h')(i)
'a'
>>> until('h')(i)
'aaaaaa'
```

## Regular Expressions

For convenience, a `regex` parser is provided, exposing functionality from the
built-in `re` module.

```python
>>> r = regex('foo|bar')
>>> r('foo')
'foo'
```

## Writing New Parsers

Any callable object can be converted to a `Parser` instance with the `parser`
function, which may be used as a decorator.

```python
from parsing import *

@parser
def quoted_string(input):
    quote_char = input.match(one_of(['"', "'"]))
    content = input.match(many(escaped(quote_char) | not_(quote_char)))
    input.match(quote_char)
    return content
```

## The `Parser` Class

All parsers are instances of `Parser` or a subclass thereof. Subclasses of
`Parser` should implement a `parse` method, which is what gets called when the
parser is used as a callable.

If the `quoted_string` example were written out in full (without the use of the
`@parser` decorator), it would look like this:

```python
from parsing import *

class quoted_string(Parser):
    def parse(self, input):
        quote_char = input.match(one_of(['"', "'"]))
        content = input.match(many(escaped(quote_char) | not_(quote_char)))
        input.match(quote_char)
        return Result(content)
```

## The `Result` Class

Parsers should return `Result` instances (when using the `@parser` decorator,
this is done automatically). A `Result` can be created simply by passing any
value or expression to the constructor, as shown above. Partial results (when
a parser finishes without parsing all the provided input) are represented by the
`PartialResult` subclass. Instances of that class must be constructed through
the `create` class method.

```python
if input:
    return PartialResult.create(some_result, input)
else:
    return Result(some_result)    
```
