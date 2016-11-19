import asyncio
import functools
import warnings

from aiohttp import web
from aiohttp.abc import AbstractView
from aiohttp_jinja2 import APP_KEY, render_template


def template(template_name, *, app_key=APP_KEY, encoding='utf-8', status=200):
    """
    Decorator compatible with aiohttp_apiset router
    """

    def wrapper(func):
        @asyncio.coroutine
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            if asyncio.iscoroutinefunction(func):
                coro = func
            else:
                coro = asyncio.coroutine(func)
            context = yield from coro(*args, **kwargs)
            if isinstance(context, web.StreamResponse):
                return context

            if 'request' in kwargs:
                request = kwargs['request']
            elif not args:
                request = None
                warnings.warn("Request not detected")
            elif isinstance(args[0], AbstractView):
                request = args[0].request
            else:
                request = args[-1]

            response = render_template(template_name, request, context,
                                       app_key=app_key, encoding=encoding)
            response.set_status(status)
            return response
        return wrapped
    return wrapper
