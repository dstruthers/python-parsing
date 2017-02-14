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
__version__ = '1.0.0'

import re
from typefu import derived, Mimic

# Core classes
class Parser(object):
    def parse(self, input):
        raise NotImplementedError

    def separated_by(self, sep):
        return sep_by(self, sep)

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

    def __mul__(self, other):
        return sequence([self for i in range(0, other)])

    def __rmul__(self, other):
        return sequence([self for i in range(0, other)])
    
    def __or__(self, other):
        return one_of([self, other])

    def __ror__(self, other):
        return one_of([other, self])

    @staticmethod
    def coerce(obj):
        if isinstance(obj, Parser):
            return obj
        elif isinstance(obj, str):
            return constant(obj)
        elif isinstance(obj, Result):
            return constant(obj.value)
        elif isinstance(obj, (list, tuple)):
            return sequence(obj)
        else:
            raise TypeError("Can't convert '{}' object to Parser implicitly".format(obj.__class__.__name__))

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
        
class Input(derived(str)):
    def __init__(self, *args, **kwargs):
        self._consumed = ''
        self._stack = []
        super(Input, self).__init__(*args, **kwargs)

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
        return parser(self)

    def rollback(self):
        self.value, self._consumed = self._stack.pop()

class Result(Mimic):
    def __init__(self, result):
        self.result = result

class PartialResult(Result):
    @classmethod
    def create(cls, value, remainder):
        result = cls(value)
        result.remainder = remainder
        return result
    
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
            parse_result = parse_func(input)
            if isinstance(parse_result, Result):
                return parse_result
            else:
                if len(input) > 0:
                    return PartialResult.create(parse_result, input)
                else:
                    return Result(parse_result)
    ParserWrapper.__name__ = parse_func.__name__
    return ParserWrapper()

# Basic parsers
class constant(Parser):
    def __init__(self, value):
        self.value = value
        
    def parse(self, input):
        if input.startswith(self.value):
            consumed = input.consume(len(self.value))
            if input:
                return PartialResult.create(consumed, input)
            else:
                return Result(consumed)
        else:
            raise mismatch(expected=repr(self.value), received=repr(input))

class regex(Parser):
    def __init__(self, pattern, flags=0, desc=''):
        self.regexp = re.compile(pattern, flags)
        if desc:
            self.desc = desc
        else:
            self.desc = 'regular expression ' + repr(pattern)

    def parse(self, input):
        matched = self.regexp.match(str(input))
        if matched:
            result = input.consume(matched.end())
            if input:
                return PartialResult.create(result, input)
            else:
                return Result(result)
        else:
            
            raise mismatch(expected=self.desc, received=repr(input))

# Combinators
class many(UnaryCombinator):
    def parse(self, input):
        parsed = ''
        while input:
            try:
                parsed += str(self.parser(input))
            except ParserError:
                break
        else:
            return Result(parsed)
        return PartialResult.create(parsed, input)

class not_(UnaryCombinator):
    def parse(self, input):
        input.begin()
        try:
            self.parser(input)
        except ParserError:
            input.rollback()
            parsed = input.consume(1)
            if input:
                return PartialResult.create(parsed, input)
            else:
                return Result(parsed)
        else:
            input.rollback()
            raise ParserError('Matched unwanted input: ' + self.parser)
        
class one_of(MultaryCombinator):
    def parse(self, input):
        for parser in self.parsers:
            try:
                return parser(input)
            except ParserError: pass
        else:
            raise ParserError('None of the supplied parsers matched the provided input')

class optional(UnaryCombinator):
    def parse(self, input):
        try:
            parsed = self.parser(input)
            if input:
                return PartialResult.create(parsed, input)
            else:
                return parsed
        except ParserError:
            return PartialResult.create('', input)

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

        if input:
            return PartialResult.create(parsed, input)
        else:
            return Result(parsed)
    
class sequence(MultaryCombinator):
    def __init__(self, parsers):
        self._iter_i = 0
        super(sequence, self).__init__(parsers)
        
    def parse(self, input):
        input.begin()
        result = ''
        try:
            for parser in self.parsers:
                result += parser(input)
        except ParserError:
            input.rollback()
            raise

        input.commit()
        if input:
            return PartialResult.create(result, input)
        else:
            return Result(result)

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

class until(UnaryCombinator):
    def parse(self, input):
        parsed = ''
        while input:
            try:
                input.begin()
                self.parser(input)
                input.rollback()
                return PartialResult.create(parsed, input)
            except EndOfInputError:
                input.rollback()
                raise
            except ParserError:
                input.rollback()
                parsed += input.consume(1)
        else:
            return Result(parsed)
    
# Complimentary instances
char = regex('.', desc='character')
digit = regex('[0-9]', desc='digit')
eof = regex('$', desc='end of input')
letter = regex('[A-Za-z]', desc='letter')
whitespace = regex('[\s\t]+', desc='whitespace')
