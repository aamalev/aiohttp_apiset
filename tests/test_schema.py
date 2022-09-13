import pytest

from aiohttp_apiset import schema
from aiohttp_apiset.schema import ParameterStyle


def test_model_repr():
    path = schema.Path(url='/', operations=[])
    path_repr = repr(path)
    assert 'None' not in path_repr


@pytest.mark.parametrize(
    'style,explode,raw_values',
    [
        (ParameterStyle.matrix, True, ';color=blue;color=black;color=brown'),
        (ParameterStyle.matrix, False, ';color=blue,black,brown'),
        (ParameterStyle.label, True, '.blue.black.brown'),
        (ParameterStyle.label, False, '.blue.black.brown'),
        (ParameterStyle.form, True, 'color=blue&color=black&color=brown'),
        (ParameterStyle.form, False, 'color=blue,black,brown'),
        (ParameterStyle.simple, True, 'blue,black,brown'),
        (ParameterStyle.simple, False, 'blue,black,brown'),
        (ParameterStyle.space_delimited, True, 'blue%20black%20brown'),
        (ParameterStyle.space_delimited, False, 'blue%20black%20brown'),
        (ParameterStyle.pipe_delimited, True, 'blue|black|brown'),
        (ParameterStyle.pipe_delimited, False, 'blue|black|brown'),
        (ParameterStyle.tab_delimited, True, 'blue\tblack\tbrown'),
        (ParameterStyle.tab_delimited, False, 'blue\tblack\tbrown'),
    ]
)
def test_parameter_parse_array_values(style, explode, raw_values):
    param = schema.Parameter(
        name='test',
        location=schema.ParameterLocation.query,
        required=True,
        style=style,
        explode=explode,
        allow_empty_value=False,
        data=None
    )
    actual_values = param.parse_array_values(raw_values)
    assert actual_values == ['blue', 'black', 'brown']


@pytest.mark.parametrize(
    'style,explode,exc',
    [
        (ParameterStyle.deep_object, True, ValueError),
        (ParameterStyle.deep_object, False, ValueError),
    ]
)
def test_parameter_parse_array_values_exception(style, explode, exc):
    param = schema.Parameter(
        name='test',
        location=schema.ParameterLocation.query,
        required=True,
        style=style,
        explode=explode,
        allow_empty_value=False,
        data=None
    )
    with pytest.raises(exc):
        param.parse_array_values('')


@pytest.mark.parametrize(
    'style,explode,raw_properties',
    [
        (ParameterStyle.matrix, True, ';R=100;G=200;B=150'),
        (ParameterStyle.matrix, False, ';color=R,100,G,200,B,150'),
        (ParameterStyle.label, True, '.R=100.G=200.B=150'),
        (ParameterStyle.label, False, '.R.100.G.200.B.150'),
        (ParameterStyle.form, True, 'R=100&G=200&B=150'),
        (ParameterStyle.form, False, 'color=R,100,G,200,B,150'),
        (ParameterStyle.simple, True, 'R=100,G=200,B=150'),
        (ParameterStyle.simple, False, 'R,100,G,200,B,150'),
        (ParameterStyle.space_delimited, True, 'R%20100%20G%20200%20B%20150'),
        (ParameterStyle.space_delimited, False, 'R%20100%20G%20200%20B%20150'),
        (ParameterStyle.pipe_delimited, True, 'R|100|G|200|B|150'),
        (ParameterStyle.pipe_delimited, False, 'R|100|G|200|B|150'),
        (ParameterStyle.deep_object, True, 'color[R]=100&color[G]=200&color[B]=150'),
        (ParameterStyle.deep_object, False, 'color[R]=100&color[G]=200&color[B]=150'),
        (ParameterStyle.tab_delimited, True, 'R\t100\tG\t200\tB\t150'),
        (ParameterStyle.tab_delimited, False, 'R\t100\tG\t200\tB\t150'),
        (ParameterStyle.json, True, '{"R": "100", "G": "200", "B": "150"}'),
        (ParameterStyle.json, False, '{"R": "100", "G": "200", "B": "150"}'),
    ]
)
def test_parameter_parse_object_properties(style, explode, raw_properties):
    param = schema.Parameter(
        name='test',
        location=schema.ParameterLocation.query,
        required=True,
        style=style,
        explode=explode,
        allow_empty_value=False,
        data=None
    )
    actual_properties = param.parse_object_properties(raw_properties)
    assert actual_properties == {'R': '100', 'G': '200', 'B': '150'}


def test_parameter_setters():
    param = schema.Parameter.cookie('test')
    assert param.name == 'test'
    assert param.location == schema.ParameterLocation.cookie
    assert param.style == schema.ParameterStyle.form
    assert param.explode
    assert not param.required
    assert not param.allow_empty_value
    assert param.data is None

    param = schema.Parameter.header('test')
    assert param.name == 'test'
    assert param.location == schema.ParameterLocation.header
    assert param.style == schema.ParameterStyle.simple
    assert not param.explode
    assert not param.required
    assert not param.allow_empty_value
    assert param.data is None

    param = schema.Parameter.path('test')
    assert param.name == 'test'
    assert param.location == schema.ParameterLocation.path
    assert param.style == schema.ParameterStyle.simple
    assert not param.explode
    assert not param.required
    assert not param.allow_empty_value
    assert param.data is None

    param = schema.Parameter.query('test')
    assert param.name == 'test'
    assert param.location == schema.ParameterLocation.query
    assert param.style == schema.ParameterStyle.form
    assert param.explode
    assert not param.required
    assert not param.allow_empty_value
    assert param.data is None

    updated_param = param.set_required(True).set_explode(False).set_style(schema.ParameterStyle.simple)
    assert updated_param is param
    updated_param = updated_param.set_allow_empty_value(True).set_schema(type_='integer')
    assert updated_param is param
    assert param.required
    assert not param.explode
    assert param.style == schema.ParameterStyle.simple
    assert param.allow_empty_value
    assert param.data is not None
    assert param.data.type_ == 'integer'
