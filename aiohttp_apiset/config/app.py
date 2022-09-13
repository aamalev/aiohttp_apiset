from enum import Enum
from typing import Any, Callable, Optional, Tuple, Union

from aiohttp import web

from ..handler import create_handler
from ..openapi.adapter import convert as convert_specification
from ..openapi.loader.base import BaseLoader
from ..parameters.extractor import ParametersExtractor
from ..parameters.payload import PayloadReader
from ..schema import OpenAPI, Operation, Path
from ..utils import import_obj, load_docstring_yaml, normalize_url
from .operation import OperationIdMapping


APP_CONFIG_KEY = 'aiohttp_apiset:swagger:config'


class UIType(str, Enum):
    swagger_ui = 'swagger_ui'
    redoc = 'redoc'


class Config:
    """
    Allows to setup application routes using OpenAPI specification config

    :param loader: A specification loader
    :param payload_reader: A custom payload reader responsible for reading request body
    :param operation_id_mapping: An Operation ID to handler mapping
    :param route_base_path: A base path override for routes
    :param ui_path: Path to Swagger-UI
    :param ui_spec_url: Default URL of the base specification file
    :param ui_type: Type of UI: swagger_ui or redoc
    :param ui_version: Version of UI (Swagger only): 2, 3, 4
    """

    def __init__(
        self,
        loader: BaseLoader,
        *,
        payload_reader: Optional[PayloadReader] = None,
        operation_id_mapping: Optional[OperationIdMapping] = None,
        route_base_path: Optional[str] = None,
        ui_path: str = '/apidoc/',
        ui_spec_url: Optional[str] = None,
        ui_type: UIType = UIType.swagger_ui,
        ui_version: int = 4,
    ):
        if not ui_path.startswith('/'):
            ui_path = '/' + ui_path
        if not ui_path.endswith('/'):
            ui_path += '/'

        if ui_version not in [2, 3, 4]:
            raise ValueError('Unexpected UI version {}'.format(ui_version))

        if payload_reader is None:
            payload_reader = PayloadReader()

        if operation_id_mapping is None:
            operation_id_mapping = OperationIdMapping()

        self.payload_reader = payload_reader
        self.loader = loader
        self.operation_id_mapping = operation_id_mapping
        self.ui_path = ui_path
        self.ui_spec_url = ui_spec_url
        self.ui_type = ui_type
        self.ui_version = ui_version

        self._route_base_path = route_base_path
        self.__specification: Optional[OpenAPI] = None

    @property
    def _specification(self) -> OpenAPI:
        if self.__specification is None:
            self.__specification = convert_specification(self.loader)
        return self.__specification

    @property
    def route_base_path(self) -> str:
        return self._route_base_path or self._specification.base_path

    def add_operation(self, method: str, path: str, handler: Union[str, Callable]):
        """
        Adds an operation to OpenAPI specification

        Handler must contain a doc comment with operation data in YAML format

        This method must be always called first

        :param method: Request method
        :param path: Path of the operation
        :param handler: Operation handler
        """
        if isinstance(handler, str):
            handler_obj = import_obj(handler)
            default_operation_id = handler
        else:
            default_operation_id = (handler.__module__ + handler.__name__)
            handler_obj = handler
        default_operation_id = default_operation_id.replace('.', '__')
        doc_comment = getattr(handler_obj, '__doc__', None)
        if doc_comment is None:
            raise ValueError('A handler has no doc comment')
        operation_data = load_docstring_yaml(doc_comment)
        if not operation_data:
            raise ValueError('A handler doc comment has no operation data')
        operation_data.setdefault('operation_id', default_operation_id)
        operation = self.loader.add_operation(path, method, operation_data)
        self.operation_id_mapping.add({operation.operation_id: handler_obj})

    def setup(self, app: web.Application, app_key: str = APP_CONFIG_KEY):
        """
        Adds routes to the given application

        :param app: Application to setup
        :param app_key: The key for storing the config in application
        """
        app[app_key] = self
        self._setup_routes(app.router)

    def _setup_routes(self, router: web.UrlDispatcher):
        for path in self._specification.paths:
            url = normalize_url(self.route_base_path + path.url)
            for operation in path.operations:
                route_name, handler = self._get_route_handler(path, operation)
                if handler is None:
                    continue
                router.add_route(operation.method, url, handler, name=route_name)

    def _get_route_handler(self, path: Path, operation: Operation) -> Tuple[Optional[str], Optional[Any]]:
        route_name = path.location_name or operation.handler_name
        raw_handler: Optional[Any] = None
        if operation.handler_name:
            raw_handler = operation.handler_name
        elif operation.operation_id and self.operation_id_mapping:
            raw_handler = self.operation_id_mapping.get(operation.operation_id)
            route_name = path.location_name or operation.operation_id

        if raw_handler is not None:
            handler = create_handler(
                handler=raw_handler,
                parameters_extractor=ParametersExtractor(
                    parameters=operation.parameters,
                    payload=operation.payload,
                    payload_reader=self.payload_reader
                )
            )
        else:
            handler = None

        return route_name, handler
