import functools
import importlib
import inspect
from typing import Any, Callable, Dict, Optional

from aiohttp import web
from aiohttp.abc import AbstractView

from .parameters.extractor import ParametersExtractor
from .utils import get_unbound_method_class, split_fqn


def create_handler(handler: Any, parameters_extractor: ParametersExtractor) -> Callable:
    view_cls, handler = _process_handler(handler)
    handler_parameters, handler_has_kwargs = _process_signature(handler)

    async def _init_view(request: web.Request) -> Optional[Any]:
        if view_cls is None:
            return None
        view = view_cls()
        if hasattr(view, 'init'):
            await view.init(request)
        else:
            view.request = request
        return view

    def _bind_parameters(items: Dict[str, Any]) -> Dict[str, Any]:
        if handler_has_kwargs:
            a, b = items, items
        else:
            a, b = {}, items
        for k, v in handler_parameters.items():
            if k in a:
                continue
            elif k in b:
                a[k] = b[k]
            elif v.default == v.empty:
                a[k] = None
        return a

    @functools.wraps(handler)
    async def wrapper(request: web.Request) -> Any:
        parameters = await parameters_extractor.extract(request)
        request.update(parameters)

        if 'request' in handler_parameters:
            parameters['request'] = request

        args = []
        view = await _init_view(request)
        if view is not None:
            args.append(view)

        parameters = _bind_parameters(parameters)

        return await handler(*args, **parameters)

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


def _process_signature(handler):
    signature = inspect.signature(handler)
    has_kwargs = False
    result = {}
    for k, v in signature.parameters.items():
        if v.name == 'self':
            continue
        if v.kind == v.VAR_KEYWORD:
            has_kwargs = True
            continue
        result[k] = v
    return result, has_kwargs


def _assert_async_handler(handler):
    if inspect.isclass(handler):
        return
    if not inspect.iscoroutinefunction(handler):
        raise TypeError('Handler must be async')
