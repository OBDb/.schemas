import pytest

from .json_formatter import tabularize

def test_basic_alignment():
    rows = [
        ['{"id": "signal1",', '"path": "path1",', '"name": "name1"}'],
        ['{"id": "sig2",', '"path": "longer_path",', '"name": "name2"}']
    ]
    expected = (
        '{"id": "signal1", "path": "path1",       "name": "name1"}',
        '{"id": "sig2",    "path": "longer_path", "name": "name2"}'
    )
    result = tabularize(rows)
    assert result == ',\n'.join(expected)

def test_empty_input():
    assert tabularize([]) == ''
    assert tabularize([[]]) == ''

def test_single_row():
    rows = [['{"id": "signal1",', '"path": "path1",', '"name": "name1"}']]
    expected = '{"id": "signal1", "path": "path1", "name": "name1"}'
    assert tabularize(rows) == expected

def test_single_column():
    rows = [
        ['{"id": "signal1"}'],
        ['{"id": "signal2"}'],
        ['{"id": "signal3"}']
    ]
    expected = (
        '{"id": "signal1"}',
        '{"id": "signal2"}',
        '{"id": "signal3"}'
    )
    assert tabularize(rows) == ',\n'.join(expected)

def test_different_length_rows():
    rows = [
        ['{"id": "signal1",', '"path": "path1"'],
        ['{"id": "sig2",', '"path": "longer_path",', '"extra": "field"}']
    ]
    expected = (
        '{"id": "signal1", "path": "path1"',
        '{"id": "sig2",    "path": "longer_path", "extra": "field"}'
    )
    assert tabularize(rows) == ',\n'.join(expected)

def test_mixed_content_types():
    rows = [
        ['123', 'abc', 'xyz'],
        ['1', 'abcdef', 'x']
    ]
    expected = (
        '123 abc    xyz',
        '1   abcdef x'
    )
    assert tabularize(rows) == ',\n'.join(expected)

if __name__ == '__main__':
    pytest.main([__file__])
