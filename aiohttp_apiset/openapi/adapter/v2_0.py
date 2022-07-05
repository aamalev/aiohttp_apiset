from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple, Union

from ... import schema as target_schema
from ...utils import remove_patterns
from ..loader.v2_0 import Loader
from ..schema import v2_0 as source_schema
from . import constants


def convert(loader: Loader) -> target_schema.OpenAPI:
    converter = Converter(loader)
    return converter.convert()


class Converter:

    PAYLOAD_LOCATIONS = [source_schema.ParameterLocation.body, source_schema.ParameterLocation.form_data]

    PARAMETER_LOCATION_MAP = {
        source_schema.ParameterLocation.query: target_schema.ParameterLocation.query,
        source_schema.ParameterLocation.header: target_schema.ParameterLocation.header,
        source_schema.ParameterLocation.path: target_schema.ParameterLocation.path,
    }

    COLLECTION_FORMAT_MAP = {
        # collection format: (parameter style, explode)
        source_schema.CollectionFormat.csv: (target_schema.ParameterStyle.form, False),
        source_schema.CollectionFormat.ssv: (target_schema.ParameterStyle.space_delimited, False),
        source_schema.CollectionFormat.tsv: (target_schema.ParameterStyle.tab_delimited, False),
        source_schema.CollectionFormat.pipes: (target_schema.ParameterStyle.pipe_delimited, False),
        source_schema.CollectionFormat.multi: (target_schema.ParameterStyle.form, True)
    }

    def __init__(self, loader: Loader):
        self.loader = loader

    def convert(self) -> target_schema.OpenAPI:
        obj = self.loader.specification
        if obj is None:
            raise RuntimeError('Specification is not loaded')

        source_paths = {}
        converted_paths = []
        for url, item in obj.paths.items():
            converted_paths.append(self._convert_path(url, item))
            url = remove_patterns(url)
            source_paths[url] = item
        obj.paths = source_paths

        return target_schema.OpenAPI(
            base_path=obj.base_path or '/',
            paths=converted_paths
        )

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
        base_parameters, base_payload = self._convert_parameters(path_item.parameters)

        result = []
        for method, operation in [
            (target_schema.OperationMethod.get, path_item.get),
            (target_schema.OperationMethod.put, path_item.put),
            (target_schema.OperationMethod.post, path_item.post),
            (target_schema.OperationMethod.delete, path_item.delete),
            (target_schema.OperationMethod.options, path_item.options),
            (target_schema.OperationMethod.head, path_item.head),
            (target_schema.OperationMethod.patch, path_item.patch),
        ]:
            if operation is None:
                continue
            parameters, payload = self._convert_parameters(operation.parameters)
            parameters = self._combine_parameters(base_parameters, parameters)
            payload = self._choose_payload(base_payload, payload)
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

    def _choose_payload(
        self,
        a: Optional[target_schema.Payload],
        b: Optional[target_schema.Payload]
    ) -> Optional[target_schema.Payload]:
        if a is not None and b is not None:
            raise ValueError('There can be one payload at most')
        if a is not None:
            return a
        if b is not None:
            return b
        return None

    def _convert_parameters(
        self,
        items: Optional[List[Union[source_schema.Ref, source_schema.Parameter]]]
    ) -> Tuple[target_schema.Parameters, Optional[target_schema.Payload]]:
        if items is None:
            return [], None

        common_parameters: List[source_schema.Parameter] = []
        payload_parameters: List[source_schema.Parameter] = []

        for item in items:
            if isinstance(item, source_schema.Ref):
                item = self.loader.resolve_ref(source_schema.Parameter, item.ref)
            if item.in_ in self.PAYLOAD_LOCATIONS:
                payload_parameters.append(item)
            else:
                common_parameters.append(item)

        parameters = self._convert_common_parameters(common_parameters)
        payload = self._convert_payload_parameters(payload_parameters)

        return parameters, payload

    def _convert_common_parameters(self, parameters: List[source_schema.Parameter]) -> target_schema.Parameters:
        return [self._convert_common_parameter(i) for i in parameters]

    def _convert_common_parameter(self, parameter: source_schema.Parameter) -> target_schema.Parameter:
        location = self.PARAMETER_LOCATION_MAP.get(parameter.in_)
        assert location is not None
        if parameter.collection_format is not None:
            collection_format = self.COLLECTION_FORMAT_MAP.get(parameter.collection_format)
            assert collection_format is not None
            style, explode = collection_format
        else:
            if location == target_schema.ParameterLocation.query:
                style = target_schema.ParameterStyle.form
            elif location == target_schema.ParameterLocation.header:
                style = target_schema.ParameterStyle.simple
            elif location == target_schema.ParameterLocation.path:
                style = target_schema.ParameterStyle.simple
            else:
                raise NotImplementedError()  # pragma: no cover
            explode = style == target_schema.ParameterStyle.form
        return target_schema.Parameter(
            name=parameter.name,
            location=location,
            required=parameter.required if parameter.required is not None else False,
            allow_empty_value=parameter.allow_empty_value if parameter.allow_empty_value is not None else False,
            style=style,
            explode=explode,
            data=self._convert_parameter_to_schema(parameter)
        )

    def _convert_payload_parameters(self, parameters: List[source_schema.Parameter]) -> Optional[target_schema.Payload]:
        TYPE_MULTIPART = target_schema.MediaContentType.multipart
        TYPE_URLENCODED = target_schema.MediaContentType.urlencoded
        TYPE_JSON = target_schema.MediaContentType.json

        ParametersMap = Dict[target_schema.MediaContentType, List[source_schema.Parameter]]

        parameters_map: ParametersMap = defaultdict(list)
        is_required = False

        for item in parameters:
            if item.in_ == source_schema.ParameterLocation.form_data:
                if item.type_ == source_schema.ParameterType.file:
                    parameters_map[TYPE_MULTIPART].append(item)
                else:
                    parameters_map[TYPE_URLENCODED].append(item)
            else:
                parameters_map[TYPE_JSON].append(item)
            if item.required is not None:
                is_required = is_required or item.required

        if TYPE_MULTIPART in parameters_map:
            parameters_map[TYPE_MULTIPART].extend(parameters_map.pop(TYPE_URLENCODED, []))

        media_types: target_schema.MediaTypes = []

        multipart_parameters = parameters_map.pop(TYPE_MULTIPART, [])
        multipart_body = self._convert_payload_form_body(TYPE_MULTIPART, multipart_parameters)
        if multipart_body is not None:
            media_types.append(multipart_body)

        urlencoded_parameters = parameters_map.pop(TYPE_URLENCODED, [])
        urlencoded_body = self._convert_payload_form_body(TYPE_URLENCODED, urlencoded_parameters)
        if urlencoded_body is not None:
            media_types.append(urlencoded_body)

        json_parameters = parameters_map.pop(TYPE_JSON, [])
        json_body = self._convert_payload_json_body(json_parameters)
        if json_body is not None:
            media_types.append(json_body)

        if media_types:
            return target_schema.Payload(
                media_types=media_types,
                required=is_required
            )

        return None

    def _convert_payload_form_body(
        self,
        content_type: target_schema.MediaContentType,
        items: List[source_schema.Parameter]
    ) -> Optional[target_schema.MediaType]:
        if not items:
            return None

        properties = {}
        requred = []

        encodings = []

        for item in items:
            if item.type_ == source_schema.ParameterType.file:
                encodings.append(
                    target_schema.Encoding(
                        property_name=item.name,
                        content_type='application/octet-stream',
                        headers=[]
                    )
                )
            else:
                properties[item.name] = self._convert_parameter_to_schema(item)

            if item.required:
                requred.append(item.name)

        return target_schema.MediaType(
            name=None,
            content_type=content_type,
            data=target_schema.Schema(
                type_='object',
                properties=properties,
                required=requred
            ),
            encodings=encodings
        )

    def _convert_payload_json_body(self, items: List[source_schema.Parameter]) -> Optional[target_schema.MediaType]:
        if not items:
            return None

        if len(items) > 1:
            raise ValueError('There can be one payload at most')

        parameter = items[0]

        return target_schema.MediaType(
            name=parameter.name,
            content_type=target_schema.MediaContentType.json,
            data=self._convert_parameter_to_schema(parameter),
            encodings=[]
        )

    def _convert_parameter_to_schema(self, parameter: source_schema.Parameter) -> target_schema.Schema:
        if parameter.schema_:
            return self._convert_swagger_schema(parameter.schema_)

        return target_schema.Schema(
            description=parameter.description,
            type_=parameter.type_,
            format_=parameter.format_,
            items=self._convert_primitive(parameter.items),
            default=parameter.default,
            maximum=parameter.maximum,
            exclusive_maximum=parameter.exclusive_maximum,
            minimum=parameter.minimum,
            exclusive_minimum=parameter.exclusive_minimum,
            max_length=parameter.max_length,
            min_length=parameter.min_length,
            pattern=parameter.pattern,
            max_items=parameter.max_items,
            min_items=parameter.min_items,
            unique_items=parameter.unique_items,
            enum=parameter.enum,
            multiple_of=parameter.multiple_of
        )

    def _convert_swagger_schema(self, schema: source_schema.Schema) -> target_schema.Schema:
        if schema.ref:
            schema = self.loader.resolve_ref(source_schema.Schema, schema.ref)
            return self._convert_swagger_schema(schema)

        return target_schema.Schema(
            ref=None,
            format_=schema.format,
            title=schema.title,
            description=schema.description,
            default=schema.default,
            multiple_of=schema.multiple_of,
            maximum=schema.maximum,
            exclusive_maximum=schema.exclusive_maximum,
            minimum=schema.minimum,
            exclusive_minimum=schema.exclusive_minimum,
            max_length=schema.max_length,
            min_length=schema.min_length,
            pattern=schema.pattern,
            max_items=schema.max_items,
            min_items=schema.min_items,
            unique_items=schema.unique_items,
            max_properties=schema.max_properties,
            min_properties=schema.min_properties,
            required=schema.required,
            enum=schema.enum,
            additional_properties=schema.additional_properties,
            type_=schema.type_,
            items=self._convert_swagger_schema_items(schema.items),
            all_of=[self._convert_swagger_schema(i) for i in schema.all_of] if schema.all_of else None,
            properties=self._convert_swagger_schema_properties(schema.properties),
            read_only=schema.read_only
        )

    def _convert_swagger_schema_items(
        self,
        items: Optional[Union[source_schema.Schema, List[source_schema.Schema]]]
    ) -> Optional[target_schema.Schema]:
        if items is None:
            return None
        if isinstance(items, source_schema.Schema):
            return self._convert_swagger_schema(items)
        raise TypeError('Could not convert a sequence of schemas into a single schema')

    def _convert_swagger_schema_properties(
        self,
        properties: Optional[Dict[str, Union[Any, source_schema.Schema]]]
    ) -> Optional[Dict[str, target_schema.Schema]]:
        if properties is None:
            return None
        result = {}
        for k, v in properties.items():
            if isinstance(v, source_schema.Schema):
                result[k] = self._convert_swagger_schema(v)
            # NOTE: we ignore all other types since there is no way to convert it to Schema
        return result

    def _convert_primitive(self, primitive: Optional[source_schema.Primitive]) -> Optional[target_schema.Schema]:
        if primitive is None:
            return None
        # NOTE: we ignore primitive.collection_format
        # since there is no way to specify collection format in Schema
        return target_schema.Schema(
            type_=primitive.type_,
            format=primitive.format_,
            items=self._convert_primitive(primitive.items),
            default=primitive.default,
            maximum=primitive.maximum,
            exclusive_maximum=primitive.exclusive_maximum,
            minimum=primitive.minimum,
            exclusive_minimum=primitive.exclusive_minimum,
            max_length=primitive.max_length,
            min_length=primitive.min_length,
            pattern=primitive.pattern,
            max_items=primitive.max_items,
            min_items=primitive.min_items,
            unique_items=primitive.unique_items,
            enum=primitive.enum,
            multiple_of=primitive.multiple_of
        )
