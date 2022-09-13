from datetime import date

import pytest

from aiohttp_apiset import utils


def test_import_obj():
    obj = utils.import_obj('datetime.date')
    assert obj is date

    with pytest.raises(ValueError):
        utils.import_obj('datetime')


@pytest.mark.parametrize('url', [
    '//api/1/../../status/',
    '/api/1/../../status/',
    '///api/1/../../status/'
])
def test_normalize_url(url):
    assert utils.normalize_url(url) == '/status/'
    assert utils.normalize_url(url.rstrip('/')) == '/status'


def test_split_fqn():
    assert utils.split_fqn('package.module.handler') == ('package.module', '', 'handler')
    assert utils.split_fqn('package.module.View.handler') == ('package.module', 'View', 'handler')
    assert utils.split_fqn('package.handler') == ('package', '', 'handler')
    with pytest.raises(ValueError, match='Unexpected FQN'):
        utils.split_fqn('')


def test_pairwise():
    assert list(utils.pairwise('ABCDEF')) == [('A', 'B'), ('C', 'D'), ('E', 'F')]
    assert list(utils.pairwise('ABCDE')) == [('A', 'B'), ('C', 'D')]


def test_load_docstring_yaml():
    data = utils.load_docstring_yaml(
        """
        Docs

        ---
        parameters:
            - name: offset
              in: query
              type: integer
        """
    )
    assert data == {
        'parameters': [
            {
                'name': 'offset',
                'in': 'query',
                'type': 'integer'
            }
        ]
    }

    data = utils.load_docstring_yaml(
        """
        Docs
        """
    )
    assert data is None

    data = utils.load_docstring_yaml(
        """
        Docs
        ---
        """
    )
    assert data is None


class Handler:
    def method(self):
        """"""


def method():
    """"""


def test_get_unbound_method_class():
    assert utils.get_unbound_method_class(Handler.method) is Handler
    assert utils.get_unbound_method_class(method) is None
