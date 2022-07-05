from typing import List, Optional, Union
from urllib.parse import urlparse

from ... import schema as target_schema
from ...utils import remove_patterns
from ..loader.v3_1 import Loader
from ..schema import v3_1 as source_schema
from . import constants


def convert(loader: Loader, base_path: Optional[str] = None) -> target_schema.OpenAPI:
    converter = Converter(loader)
    return converter.convert(base_path)


class Converter:

    DEFAULT_BASE_PATH = '/'

    PARAMETER_LOCATION_MAP = {
        source_schema.ParameterLocation.query: target_schema.ParameterLocation.query,
        source_schema.ParameterLocation.header: target_schema.ParameterLocation.header,
        source_schema.ParameterLocation.path: target_schema.ParameterLocation.path,
        source_schema.ParameterLocation.cookie: target_schema.ParameterLocation.cookie,
    }

    PARAMETER_STYLE_MAP = {
        source_schema.ParameterStyle.matrix: target_schema.ParameterStyle.matrix,
        source_schema.ParameterStyle.label: target_schema.ParameterStyle.label,
        source_schema.ParameterStyle.form: target_schema.ParameterStyle.form,
        source_schema.ParameterStyle.simple: target_schema.ParameterStyle.simple,
        source_schema.ParameterStyle.space_delimited: target_schema.ParameterStyle.space_delimited,
        source_schema.ParameterStyle.pipe_delimited: target_schema.ParameterStyle.pipe_delimited,
        source_schema.ParameterStyle.deep_object: target_schema.ParameterStyle.deep_object,
    }

    def __init__(self, loader: Loader):
        self.loader = loader

    def convert(self, base_path: Optional[str] = None) -> target_schema.OpenAPI:
        obj = self.loader.specification
        if obj is None:
            raise RuntimeError('Specification is not loaded')

        converted_paths = []
        if obj.paths:
            source_paths = {}
            for url, item in obj.paths.items():
                converted_paths.append(self._convert_path(url, item))
                url = remove_patterns(url)
                source_paths[url] = item
            obj.paths = source_paths

        if base_path is None:
            base_path = self._detect_base_path(obj.servers)

        return target_schema.OpenAPI(
            base_path=base_path,
            paths=converted_paths
        )

    def _detect_base_path(self, servers: Optional[List[source_schema.Server]]) -> str:
        for server in servers or ():
            url = server.url

            # cut schema in order to handle variables (if any) properly
            # >>> urlparse('{schema}://{domain}/api').path
            # '{schema}://{domain}/api
            # >>> urlparse('//{domain}/api').path
            # '/api'

            pos = url.find('://')
            if pos >= 0:
                url = url[pos + 1:]

            path = urlparse(server.url).path
            if path:
                # let's return first non empty path
                # user can override base path if there are many servers and it is a problem
                return path

        return self.DEFAULT_BASE_PATH

    def _convert_path(self, url: str, item: source_schema.PathItem) -> target_schema.Path:
        if item.ref is not None:
            item = self.loader.resolve_ref(source_schema.PathItem, item.ref)
            return self._convert_path(url, item)

        return target_schema.Path(
            url=url,
            location_name=getattr(item, constants.LOCATION_NAME, None),
            operations=self._convert_operations(item)
        )

    def _convert_operations(self, path_item: source_schema.PathItem) -> target_schema.Operations:
        result = []
        base_parameters = self._convert_parameters(path_item.parameters)
        for method, operation in [
            (target_schema.OperationMethod.get, path_item.get),
            (target_schema.OperationMethod.put, path_item.put),
            (target_schema.OperationMethod.post, path_item.post),
            (target_schema.OperationMethod.delete, path_item.delete),
            (target_schema.OperationMethod.options, path_item.options),
            (target_schema.OperationMethod.head, path_item.head),
            (target_schema.OperationMethod.patch, path_item.patch),
            (target_schema.OperationMethod.trace, path_item.trace),
        ]:
            if operation is None:
                continue
            parameters = self._convert_parameters(operation.parameters)
            payload = self._convert_request_body(operation.request_body)
            parameters = self._combine_parameters(base_parameters, parameters)
            result.append(target_schema.Operation(
                method=method,
                handler_name=getattr(operation, constants.HANDLER, None),
                operation_id=operation.operation_id,
                parameters=parameters,
                payload=payload
            ))
        return result

    def _combine_parameters(
        self,
        a: target_schema.Parameters,
        b: target_schema.Parameters
    ) -> target_schema.Parameters:
        mapping = {(i.name, i.location): i for i in a}
        for i in b:
            mapping[i.name, i.location] = i
        return list(mapping.values())

    def _convert_parameters(
        self,
        items: Optional[List[Union[source_schema.Parameter, source_schema.Reference]]]
    ) -> target_schema.Parameters:
        result: target_schema.Parameters = []

        if items is None:
            return result

        for item in items:
            if isinstance(item, source_schema.Reference):
                item = self.loader.resolve_ref(source_schema.Parameter, item.ref)
            result.append(self._convert_parameter(item))

        return result

    def _convert_parameter(self, parameter: source_schema.Parameter) -> target_schema.Parameter:
        location = self.PARAMETER_LOCATION_MAP.get(parameter.location)
        assert location is not None

        style = self._convert_parameter_style(parameter.style)
        if style is None:
            if location == target_schema.ParameterLocation.query:
                style = target_schema.ParameterStyle.form
            elif location == target_schema.ParameterLocation.header:
                style = target_schema.ParameterStyle.simple
            elif location == target_schema.ParameterLocation.path:
                style = target_schema.ParameterStyle.simple
            elif location == target_schema.ParameterLocation.cookie:
                style = target_schema.ParameterStyle.form
            else:
                raise NotImplementedError()  # pragma: no cover

        if parameter.explode is None:
            explode = style == target_schema.ParameterStyle.form
        else:
            explode = parameter.explode

        data = None
        if parameter.schema_ is not None:
            data = self._convert_schema(parameter.schema_)
        elif parameter.content:
            content_type, media_type = next(iter(parameter.content.items()))
            content_type = content_type.lower()
            if content_type.startswith('application/') and content_type.endswith('json'):
                data = self._convert_schema(media_type.schema_)
                style = target_schema.ParameterStyle.json

        return target_schema.Parameter(
            name=parameter.name,
            location=location,
            required=parameter.required or False,
            allow_empty_value=parameter.allow_empty_value or False,
            style=style,
            explode=explode,
            data=data
        )

    def _convert_request_body(
        self,
        body: Optional[Union[source_schema.RequestBody, source_schema.Reference]]
    ) -> Optional[target_schema.Payload]:
        if body is None:
            return None

        if isinstance(body, source_schema.Reference):
            body = self.loader.resolve_ref(source_schema.RequestBody, body.ref)
        media_types = []
        for content_type, media_type in body.content.items():
            encodings = []
            if media_type.encoding:
                for property_name, encoding in media_type.encoding.items():
                    encodings.append(self._convert_encoding(property_name, encoding))
            media_types.append(target_schema.MediaType(
                name=None,
                content_type=content_type,
                data=self._convert_schema(media_type.schema_),
                encodings=encodings
            ))
        return target_schema.Payload(media_types=media_types, required=body.required or False)

    def _convert_encoding(self, property_name: str, encoding: source_schema.Encoding) -> target_schema.Encoding:
        headers = []
        if encoding.headers:
            for header_name, header in encoding.headers.items():
                headers.append(self._convert_header(header_name, header))
        return target_schema.Encoding(
            property_name=property_name,
            content_type=encoding.content_type,
            headers=headers,
            style=self._convert_parameter_style(encoding.style),
            explode=encoding.explode,
            allow_reserved=encoding.allow_reserved
        )

    def _convert_header(
        self,
        name: str,
        header: Union[source_schema.Header, source_schema.Reference]
    ) -> target_schema.Header:
        if isinstance(header, source_schema.Reference):
            header = self.loader.resolve_ref(source_schema.Header, header.ref)
        return target_schema.Header(
            name=name,
            required=header.required or False,
            allow_empty_value=header.allow_empty_value or False,
            style=self._convert_parameter_style(header.style),
            explode=header.explode,
            data=self._convert_schema(header.schema_)
        )

    def _convert_schema(self, schema: Optional[source_schema.Schema]) -> Optional[target_schema.Schema]:
        if schema is None:
            return None
        if schema.ref:
            schema = self.loader.resolve_ref(source_schema.Schema, schema.ref)
            return self._convert_schema(schema)

        for property_name in [
            'unevaluated_items',
            'unevaluated_properties',
            'content_schema',
            'items',
            'contains',
            'additional_properties',
            'property_names',
            'if_',
            'then',
            'else_',
            'not_'
        ]:
            property_value = getattr(schema, property_name)
            if not isinstance(property_value, bool):
                property_value = self._convert_schema(property_value)
            if property_value is not None:
                setattr(schema, property_name, property_value)

        for property_name in [
            'prefix_items',
            'all_of',
            'any_of',
            'one_of',
        ]:
            property_value = getattr(schema, property_name)
            if property_value is None:
                continue
            property_value = [self._convert_schema(i) for i in property_value]
            setattr(schema, property_name, property_value)

        for property_name in [
            'properties',
            'pattern_properties',
            'dependent_schemas'
        ]:
            property_value = getattr(schema, property_name)
            if property_value is None:
                continue
            property_value = {k: self._convert_schema(v) for k, v in property_value.items()}
            setattr(schema, property_name, property_value)

        return schema

    def _convert_parameter_style(
        self,
        style: Optional[source_schema.ParameterStyle]
    ) -> Optional[target_schema.ParameterStyle]:
        if style is None:
            return None
        return self.PARAMETER_STYLE_MAP.get(style)
