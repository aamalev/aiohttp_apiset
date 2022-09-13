import functools
import importlib
import inspect
from typing import Any, Callable, Optional

from aiohttp import web
from aiohttp.abc import AbstractView

from .parameters.extractor import ParametersExtractor
from .utils import get_unbound_method_class, split_fqn


def create_handler(handler: Any, parameters_extractor: ParametersExtractor) -> Callable:
    view_cls, handler = _process_handler(handler)
    handler_signature = inspect.signature(handler)

    async def _init_view(request: web.Request) -> Optional[Any]:
        if view_cls is None:
            return None
        view = view_cls()
        if hasattr(view, 'init'):
            await view.init(request)
        else:
            view.request = request
        return view

    @functools.wraps(handler)
    async def wrapper(request: web.Request) -> Any:
        parameters = await parameters_extractor.extract(request)
        request.update(parameters)

        if 'request' in handler_signature.parameters:
            parameters['request'] = request

        args, kwargs = _bind_parameters(handler_signature, parameters)

        view = await _init_view(request)
        if view is not None:
            args.insert(0, view)

        return await handler(*args, **kwargs)

    return wrapper


def _process_handler(handler):
    view_cls = None

    if not isinstance(handler, str):
        _assert_async_handler(handler)
        view_cls = get_unbound_method_class(handler)
        return view_cls, handler

    package_path, view_name, handler_name = split_fqn(handler)
    package = importlib.import_module(package_path)
    if not view_name:
        return view_cls, getattr(package, handler_name)

    view_cls = getattr(package, view_name)
    if issubclass(view_cls, AbstractView):
        handler = view_cls
        view_cls = None
    else:
        handler = getattr(view_cls, handler_name)
    _assert_async_handler(handler)

    return view_cls, handler


def _bind_parameters(signature, data):
    args = []
    kwargs = {}
    has_var_positional = False
    has_var_keyword = False

    for parameter_name, parameter in signature.parameters.items():
        if parameter_name == 'self':
            continue

        if parameter.kind == parameter.VAR_POSITIONAL:
            has_var_positional = True
            continue

        if parameter.kind == parameter.VAR_KEYWORD:
            has_var_keyword = True
            continue

        parameter_value = data.pop(parameter_name, None)
        if parameter.kind == parameter.POSITIONAL_ONLY or parameter.kind == parameter.POSITIONAL_OR_KEYWORD:
            args.append(parameter_value)
        elif parameter.kind == parameter.KEYWORD_ONLY:
            kwargs[parameter_name] = parameter_value

    if has_var_keyword:
        kwargs.update(data)
    elif has_var_positional and data:
        args.extend(data.values())

    return args, kwargs


def _assert_async_handler(handler):
    if inspect.isclass(handler):
        return
    if not inspect.iscoroutinefunction(handler):
        raise TypeError('Handler must be async')
