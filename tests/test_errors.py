import pytest

from aiohttp_apiset.errors import Errors


def test_errors():
    errors = Errors(
        'test',
        key='value',
        list_items=['l1', 'l2'],
        tuple_items=['t1', 't2'],
        sub_errors=Errors('sub error')
    )

    assert errors[None] is errors
    assert errors['key']._errors == ('value',)
    assert errors.key is errors['key']

    assert list(errors) == [None, 'key', 'list_items', 'tuple_items', 'sub_errors']
    assert len(errors) == 5
    assert bool(errors)
    assert repr(errors).startswith('<Errors')

    errors.add('new', 'new-value')
    assert errors['new']._errors == ('new-value', )

    errors.extend([('extened', 'extended-value')])
    assert errors['extened']._errors == ('extended-value', )

    errors.update([('updated_list', 'updated-list-value')])
    assert errors['updated_list']._errors == ('updated-list-value', )
    errors.update((('updated_tuple', 'updated-tuple-value'), ))
    assert errors['updated_tuple']._errors == ('updated-tuple-value', )

    errors.update(Errors('test-update-with-errors', updated_errors_key='value'))
    assert 'test-update-with-errors' in errors._errors
    assert errors.updated_errors_key._errors == ('value', )

    errors.add('level1', 'level2', 'level3', 'level4')

    with pytest.raises(TypeError, match='Unexpected values'):
        errors.update(object())

    assert errors.to_tree() == {
        'key': ['value'],
        'list_items': ['l1', 'l2'],
        'tuple_items': ['t1', 't2'],
        'sub_errors': ['sub error'],
        'new': ['new-value'],
        'extened': ['extended-value'],
        'updated_list': ['updated-list-value'],
        'updated_tuple': ['updated-tuple-value'],
        'updated_errors_key': ['value'],
        'level1': {'level2': {'level3': ['level4']}},
        '.': ['test', 'test-update-with-errors']
    }

    assert errors.to_flat() == {
        'key': ['value'],
        'list_items': ['l1', 'l2'],
        'tuple_items': ['t1', 't2'],
        'sub_errors': ['sub error'],
        'new': ['new-value'],
        'extened': ['extended-value'],
        'updated_list': ['updated-list-value'],
        'updated_tuple': ['updated-tuple-value'],
        'updated_errors_key': ['value'],
        'level1.level2.level3': ['level4'],
        '.': ['test', 'test-update-with-errors'],
    }

    with pytest.raises(TypeError, match='Unexpected error type'):
        Errors(key=object())

    errors = Errors()
    assert errors.to_tree() is None
    assert errors.to_flat() == {}

    errors = Errors(child=Errors())
    assert errors.to_tree() is None
    assert errors.to_flat() == {}
