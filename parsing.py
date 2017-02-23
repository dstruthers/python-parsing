"""Combinatorial parsing framework"""

# Copyright (c) 2017 Darren M. Struthers <dstruthers@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

__author__ = 'Darren M. Struthers <dstruthers@gmail.com>'
__version__ = '1.0.0-dev'

import collections.abc
import re

# Core classes
class Parser(object):
    def parse(self, input):
        raise NotImplementedError

    def separated_by(self, sep):
        return sep_by(self, sep)

    def surrounded_by(self, outer):
        return self.coerce(outer) + self + self.coerce(outer)

    def __call__(self, input):
        if isinstance(input, Input):
            return self.parse(input)
        else:
            return self.parse(Input(input))

    def __add__(self, other):
        if isinstance(other, sequence):
            other.insert(0, self)
            return other
        elif isinstance(self, sequence):
            self.append(self.coerce(other))
            return self
        else:
            return sequence([self, self.coerce(other)])

    def __radd__(self, other):
        if isinstance(other, sequence):
            other.append(self)
            return other
        elif isinstance(self, sequence):
            self.insert(0, self.coerce(other))
            return self
        else:
            return sequence([self.coerce(other), self])

    def __invert__(self):
        return not_(self)
    
    def __mul__(self, other):
        return repeat(self, other)

    def __rmul__(self, other):
        return repeat(self, other)

    def __or__(self, other):
        if isinstance(other, one_of):
            return one_of([self] + other.parsers)
        else:
            return one_of([self, other])

    def __ror__(self, other):
        if isinstance(other, one_of):
            return one_of(other.parsers + [self])
        else:
            return one_of([other, self])

    def __rshift__(self, other):
        if callable(other):
            return Pipe(self, other)
        else:
            return Pipe(self, lambda *_, **__: other)
        
    def __rrshift__(self, other):
        if callable(other):
            return Pipe(other, self)
        else:
            return Pipe(lambda *_, **__: other, self)

    # can this now coerce anything since Input has been refactored to allow any type?
    @staticmethod
    def coerce(obj):
        if isinstance(obj, Parser):
            return obj
        elif isinstance(obj, QualifiedResult):
            return constant(obj.result)
        elif isinstance(obj, str):
            return constant(obj)
        elif isinstance(obj, collections.abc.Iterable):
            return sequence(obj)
        else:
            return constant(obj)

class repeat(Parser):
    def __init__(self, parser, times):
        self.parser = self.coerce(parser)
        self.times = times

    def parse(self, input):
        parsed = Nil
        for i in range(0, self.times):
            parsed += self.parser(input)
        return parsed

    def __mul__(self, other):
        return repeat(self.parser, self.times * other)
        
    def __rmul__(self, other):
        return repeat(self.parser, self.times * other)
    
class UnaryCombinator(Parser):
    def __init__(self, parser):
        self.parser = self.coerce(parser)

class BinaryCombinator(Parser):
    def __init__(self, parser1, parser2):
        self.parser1 = self.coerce(parser1)
        self.parser2 = self.coerce(parser2)

class MultaryCombinator(Parser):
    def __init__(self, parsers):
        self.parsers = [self.coerce(p) for p in parsers]

class Input(object):
    def __init__(self, value):
        if not isinstance(value, collections.abc.Sequence):
            raise TypeError('{} not a sequence type.'.format(value.__class__))
        self.value = value
        self._consumed = ''
        self._stack = []

    def begin(self):
        self._stack.append((self.value, self._consumed))

    def commit(self):
        self._stack.pop()
        
    def consume(self, chars):
        if len(self.value) >= chars:
            consumed = self.value[0:chars]
            self._consumed += consumed
            self.value = self.value[chars:]
            return consumed
        else:
            raise EndOfInputError('End of input or insufficient input for request')

    def match(self, parser):
        if not isinstance(parser, Parser):
            parser = Parser.coerce(parser)
        saved_value = self.value
        result = parser(self)
        matched = saved_value[0:len(saved_value) - len(self.value)]
        return Match(result, matched)

    def rollback(self):
        self.value, self._consumed = self._stack.pop()

    def __eq__(self, other):
        return self.value == other

    def __getitem__(self, offset):
        return self.value[offset]

    def __len__(self):
        return len(self.value)

    def __radd__(self, other):
        return other + self.value

    def __repr__(self):
        return repr(self.value)

class QualifiedResult(object):
    def __add__(self, other):
        return self.result + other
    
    def __eq__(self, other):
        return self.result == other

    def __getitem__(self, offset):
        return self.result[offset]

    def __len__(self):
        return len(self.result)

    def __radd__(self, other):
        return other + self.result
    
class Match(QualifiedResult):
    def __init__(self, result, matched):
        self.result = result
        self.matched = matched
    
class Partial(QualifiedResult):
    def __init__(self, result, remainder):
        self.result = result
        self.remainder = remainder

class Nil(object):
    def __add__(self, other):
        return other

    def __eq__(self, other):
        if type(other) is self.__class__:
            return True
        elif isinstance(other, dict):
            return other == {}
        elif isinstance(other, list):
            return other == []
        elif isinstance(other, set):
            return other == set()
        elif isinstance(other, str):
            return other == ''
        else:
            raise TypeError("Cannot compare Nil object to '{}'".format(other.__class__.__name__))
        
    def __radd__(self, other):
        return other

    def __repr__(self):
        return 'Nil'

    def __str__(self):
        return 'Nil'

Nil = Nil()
        
# Errors
class ParserError(Exception): pass
class EndOfInputError(ParserError): pass

def mismatch(expected='', received=''):
    if not received or received == repr(''):
        return EndOfInputError('Expected {} but encountered end of input'.format(expected))
    else:
        return ParserError('Expected {} but received {}'.format(expected, received))
    
# Decorators
def parser(parse_func):
    class ParserWrapper(Parser):
        def parse(self, input):
            return parse_func(input)
    ParserWrapper.__name__ = parse_func.__name__
    return ParserWrapper()

# Basic parsers
class constant(Parser):
    def __init__(self, value):
        self.value = value
        
    def parse(self, input):
        if input[0:len(self.value)] == self.value:
            return input.consume(len(self.value))
        else:
            raise mismatch(expected=repr(self.value), received=repr(input))

    def __mul__(self, other):
        return constant(self.value * other)

    def __rmul__(self, other):
        return constant(self.value * other)

class regex(Parser):
    def __init__(self, pattern, flags=0, desc=''):
        self.regexp = re.compile(pattern, flags)
        if desc:
            self.desc = desc
        else:
            self.desc = 'regular expression ' + repr(pattern)

    def parse(self, input):
        matched = self.regexp.match(input.value)
        if matched:
            return input.consume(matched.end())
        else:
            raise mismatch(expected=self.desc, received=repr(input))

# Pre- and Post-Processing
class Pipe(Parser):
    def __init__(self, in_fn, out_fn):
        self.in_fn = in_fn
        self.out_fn = out_fn

    def __call__(self, *args, **kwargs):
        return self.out_fn(self.in_fn(*args, **kwargs))

    def parse(self, input):
        return self(input)

    def __rshift__(self, other):
        return Pipe(self, other)

    def __rrshift__(self, other):
        return Pipe(other, self)
        
# Combinators
class ignored(UnaryCombinator):
    def parse(self, input):
        self.parser(input)
        return Nil

class many(UnaryCombinator):
    def __init__(self, parser, at_least=0):
        self.at_least = at_least
        super(many, self).__init__(parser)
        
    def parse(self, input):
        parsed = Nil
        count = 0

        input.begin()        
        while input:
            try:
                parsed += self.parser(input)
                count += 1
            except ParserError:
                break

        if count >= self.at_least:
            input.commit()
            return parsed
        else:
            input.rollback()
            raise mismatch(expected='at least {} occurrences of {}'.format(self.at_least, self.parser), received=input)

class not_(UnaryCombinator):
    def parse(self, input):
        input.begin()
        try:
            self.parser(input)
        except ParserError:
            input.rollback()
            return input.consume(1)
        else:
            input.rollback()
            raise ParserError('Matched unwanted input: ' + input)
        
class one_of(MultaryCombinator):
    def parse(self, input):
        for parser in self.parsers:
            input.begin()
            try:
                result = parser(input)
                input.commit()
                return result
            except ParserError:
                input.rollback()
        else:
            raise ParserError('None of the supplied parsers matched the provided input')

class optional(UnaryCombinator):
    def parse(self, input):
        try:
            return self.parser(input)
        except ParserError:
            return Nil

class peek(UnaryCombinator):
    def parse(self, input):
        input.begin()
        try:
            self.parser(input)
            input.rollback()
            return Nil
        except ParserError:
            input.rollback()
            raise

# Consider merging with sequence. Add separator= keyword argument
class sep_by(BinaryCombinator):
    def parse(self, input):
        parser = self.parser1
        separator = self.parser2
        parsed = []
        
        while input:
            try:
                input.begin()
                if parsed:
                    input.match(separator)
                parsed.append(input.match(parser))
            except ParserError:
                input.rollback()
                break
            else:
                input.commit()

        return parsed

# Consider adding keyword arguments such as output_type, then use some kind of
# monoid framework for construction
class sequence(MultaryCombinator):
    def __init__(self, parsers):
        self._iter_i = 0
        super(sequence, self).__init__(parsers)
        
    def parse(self, input):
        input.begin()
        result = Nil
        try:
            for parser in self.parsers:
                result += parser(input)
        except ParserError:
            input.rollback()
            raise

        input.commit()
        return result

    # Make sequences iterable
    def __iter__(self):
        return self

    def __next__(self):
        if self._iter_i < len(self.parsers):
            result = self.parsers[self._iter_i]
            self._iter_i += 1
            return result
        else:
            raise StopIteration

    def next(self):
        return self.__next__()

    # Expose some list methods for convenience
    def append(self, *args, **kwargs):
        self.parsers.append(*args, **kwargs)

    def insert(self, *args, **kwargs):
        self.parsers.insert(*args, **kwargs)

    def pop(self, *args, **kwargs):
        return self.parsers.pop(*args, **kwargs)

# should this combinator fail if its operand is never encountered?
class until(UnaryCombinator):
    def parse(self, input):
        parsed = Nil
        while input:
            try:
                input.begin()
                self.parser(input)
                input.rollback()
                return parsed
            except EndOfInputError:
                input.rollback()
                raise
            except ParserError:
                input.rollback()
                parsed += input.consume(1)
        else:
            return parsed
    
# Complimentary instances
char = regex('.', desc='character')
digit = regex('[0-9]', desc='digit')
eof = regex('$', desc='end of input')
letter = regex('[A-Za-z]', desc='letter')
whitespace = regex('[\s\t]+', desc='whitespace')
word_boundary = regex('[\s\.,;\'\"!\?\(\)]+', desc='word boundary')

def escaped(c):
    @parser
    def escaped_char(input):
        input.match('\\')
        return input.match(c)
    return escaped_char

def trimmed(parser):
    return Parser.coerce(parser).surrounded_by(ignored(optional(whitespace)))
