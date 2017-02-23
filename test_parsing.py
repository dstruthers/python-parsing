import pytest
import re
from random import randint

from parsing import *

# Test types, casting, operator overloading
def test_parser_add():
    p = constant('foo') + 'bar'
    assert(isinstance(p, sequence))
    
def test_parser_radd():
    p = 'foo' + constant('bar')
    assert(isinstance(p, sequence))

def test_constant_mul():
    p = constant('foo') * 3
    assert(isinstance(p, constant))

def test_constant_rmul():
    p = 3 * constant('foo')
    assert(isinstance(p, constant))

def test_other_mul():
    p = one_of(['foo', 'bar']) * 3
    print(repeat.__doc__)
    assert(isinstance(p, repeat))

def test_other_rmul():
    p = 3 * one_of(['foo', 'bar'])
    assert(isinstance(p, repeat))
    
def test_parser_or():
    p = constant('foo') | constant('bar')
    assert(isinstance(p, one_of))

def test_parser_ror():
    p = 'foo' | constant('bar')
    assert(isinstance(p, one_of))

def test_coerce_str_to_constant():
    assert(isinstance(Parser.coerce('foo'), constant))

def test_coerce_list_to_sequence():
    assert(isinstance(Parser.coerce(['foo']), sequence))

def test_coerce_tuple_to_sequence():
    assert(isinstance(Parser.coerce(('foo',)), sequence))

def test_coerce_parser_no_effect():
    parser = constant('foo')
    coerced = Parser.coerce(parser)
    assert(parser == coerced)

# Test behavior of base classes and their constructors
def test_unary_constructor():
    p = UnaryCombinator('foo')
    assert(hasattr(p, 'parser'))
    assert(isinstance(p.parser, Parser))

def test_binary_constructor():
    p = BinaryCombinator('foo', 'bar')
    assert(hasattr(p, 'parser1'))
    assert(hasattr(p, 'parser2'))
    assert(isinstance(p.parser1, Parser))
    assert(isinstance(p.parser2, Parser))

def test_multary_combinator():
    p = MultaryCombinator(['foo', 'bar', 'baz'])
    assert(hasattr(p, 'parsers'))
    return all([isinstance(x, Parser) for x in p.parsers])

# Test exception types
def test_mismatch():
    assert(isinstance(mismatch(expected='foo', received='bar'), ParserError))

@pytest.mark.xfail(raises=ParserError)
def test_error_type():
    constant('foo')('bar')
    
# Test behavior of Result instances
def test_result():
    parser = constant('foo')
    complete_result = parser('foo')
    partial_result = parser('foobar')

    assert(isinstance(complete_result, str))
    #assert(partial_result.remainder == 'bar')
    #assert(isinstance(complete_result, Result))
    #assert(not(isinstance(complete_result, PartialResult)))
    #assert(isinstance(partial_result, Result))
    #assert(isinstance(partial_result, PartialResult))
    #assert(partial_result.remainder == 'bar')

# Test decorator behavior
def test_parser_decorator():
    @parser
    def simple_parser(input):
        matched = input.match('foo')
        return [matched]

    assert(isinstance(simple_parser, Parser))

    result = simple_parser('foo')
    assert(isinstance(result, list))
    assert(result == ['foo'])

# Test associativity of binary operators
def test_plus_associativity():
    foo = constant('foo')
    bar = constant('bar')
    baz = constant('baz')

    p1 = (foo + bar) + baz
    p2 = foo + (bar + baz)
    assert(p1('foobarbaz') == p2('foobarbaz'))

def test_or_associativity():
    p1 = (constant('foobar') | constant('foo')) | constant('f')
    p2 = constant('foobar') | (constant('foo') | constant('f'))

    assert(p1('foobar') == p2('foobar'))
    assert(p1('foo') == p2('foo'))
    assert(p1('f') == p2('f'))

def test_rshift_associativity():
    p1 = (constant('foo') >> str.upper) >> constant('FOO')
    p2 = constant('foo') >> (str.upper >> constant('FOO'))
    assert(p1('foo') == p2('foo'))
    
# Test provided Parser subclasses
def random_str(length=16):
    """Return random string with the specified length."""
    s = ''
    while len(s) < length:
        s += chr(randint(33, 127))
    return s

def repeated(test_fn):
    """Decorator that produces a test which will repeat 100 times."""
    def repeat_decorator(*args, **kwargs):
        for i in range(0, 100):
            test_fn(*args, **kwargs)
    return repeat_decorator

@repeated
def test_constant():
    r = random_str()
    parser = constant(r)
    assert(parser(r) == r)

@repeated
def test_regex():
    r = random_str()
    parser = regex('^{}$'.format(re.escape(r)))
    assert(parser(r) == r)

@repeated
def test_many():
    r = random_str()
    parser = many(r)
    assert(parser(r * 10) == r * 10)

@pytest.mark.xfail(raises=ParserError)
@repeated
def test_many_at_least():
    r = random_str()
    parser = many(r, at_least=11)
    parser(r * 10)
    
@repeated
def test_not():
    avoid = random_str()
    prefix = random_str(length=1)
    result = not_(avoid)(prefix + avoid)
    #assert(isinstance(result, Partial))
    assert(result == prefix)
    #assert(result.remainder == avoid)

@repeated
def test_one_of():
    tokens = [random_str() for i in range(0, 5)]
    parser = one_of(tokens)
    assert(parser(tokens[3]) == tokens[3])

@repeated
def test_optional():
    pattern = random_str()
    alternative = random_str()
    parser = optional(pattern)
    assert(parser(pattern) == pattern)
    assert(parser(alternative) == '')

@repeated
def test_peek():
    pattern = random_str()
    parser = peek(pattern)
    assert(parser(pattern) == '')
    assert(parser(pattern) == '')
    
@repeated
def test_sep_by():
    tokens = [random_str() for i in range(0, 5)]
    separator = random_str()
    assert(sep_by(one_of(tokens), separator)(separator.join(tokens)) == tokens)

@repeated
def test_sequence():
    tokens = [random_str() for i in range(0, 5)]
    parser = sequence(tokens)
    assert(parser(''.join(tokens)) == ''.join(tokens))

@repeated
def test_until():
    pattern = random_str()
    prefix = random_str()
    parser = until(pattern)
    assert(parser(prefix + pattern) == prefix)

@repeated
def test_surrounded_by():
    pattern = random_str()
    outer = random_str()
    parser = constant(pattern).surrounded_by(outer)
    assert(isinstance(parser, sequence))
    assert(parser(outer + pattern + outer) == outer + pattern + outer)

@repeated
def test_ignored():
    pattern = random_str()
    parser = ignored(pattern)
    result = parser(pattern)
    #assert(isinstance(result, Result) and not(isinstance(result, PartialResult)))
    #assert(not(isinstance(result, Partial)))
    assert(result == '')

@repeated
def test_trimmed():
    pattern = random_str()
    parser = trimmed(pattern)
    assert(parser('   ' + pattern + '   ') == pattern)

@repeated
def test_input_match_vs_parser_call():
    pattern = random_str()
    parser = constant(pattern)
    assert(parser(Input(pattern)) == Input(pattern).match(parser))
