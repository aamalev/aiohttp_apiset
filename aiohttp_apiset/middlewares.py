import asyncio
from dataclasses import dataclass
from functools import partial
from typing import List, Optional, Union

from aiohttp import hdrs, web
from multidict import MultiDict

from .json_encoder import JsonEncoder
from .validator import ValidationError


def jsonify(*, encoder: Optional[JsonEncoder] = None, **kwargs):
    if encoder is None:
        encoder = JsonEncoder.class_factory(**kwargs)

    json_response = partial(web.json_response, dumps=encoder.dumps)

    @web.middleware
    async def middleware(request: web.Request, handler):
        try:
            response = await handler(request)
        except ValidationError as exc:
            return json_response({'errors': exc}, status=400)
        except web.HTTPException as exc:
            if exc.status > 399:
                return json_response({'error': exc.reason}, status=exc.status)
            raise exc
        else:
            if isinstance(response, asyncio.Future):
                response = await response
            if isinstance(response, dict):
                status = response.get('status', 200)
                if not isinstance(status, int):
                    status = 200
                return json_response(response, status=status)
            elif not isinstance(response, web.StreamResponse):
                return json_response(response)
            return response

    return middleware


@web.middleware
async def binary(request: web.Request, handler) -> web.Response:
    response = await handler(request)
    if isinstance(response, (bytes, bytearray, memoryview)):
        return web.Response(body=response)
    elif isinstance(response, str):
        return web.Response(text=response)
    else:
        return response


@dataclass
class CorsConfig:
    """
    Cross-Origin Resource Sharing middleware configration

    :param allow_origin: Specifies either a single origin which tells browsers
                         to allow that origin to access the resource;
                         or else — for requests without credentials —
                         the "*" wildcard tells browsers
                         to allow any origin to access the resource.
    :param allow_credentials: Indicates whether or not the response to the request
                              can be exposed when the credentials flag is true.
                              When used as part of a response to a preflight request,
                              this indicates whether or not the actual request can be made using credentials.
                              Note that simple GET requests are not preflighted,
                              and so if a request is made for a resource with credentials,
                              if this header is not returned with the resource,
                              the response is ignored by the browser and not returned to web content.
    :param allow_headers: Is used in response to a preflight request to indicate which HTTP headers
                          can be used when making the actual request.
                          This header is the server side response
                          to the browser's Access-Control-Request-Headers header.
    :param allow_requested_headers: Sets allow_headers to a list of headers got from Access-Control-Request-Headers
    :param allow_methods: Specifies the method or methods allowed when accessing the resource.
                          This is used in response to a preflight request.
                          The conditions under which a request is preflighted are discussed above.
    :param expose_headers: Adds the specified headers to the allowlist that browsers is allowed to access.
    :param max_age: Indicates how long the results of a preflight request can be cached.
    """
    allow_origin: Union[str, List[str]] = '*'
    allow_credentials: bool = False
    allow_headers: Optional[List[str]] = None
    allow_requested_headers: bool = False
    allow_methods: Optional[List[str]] = None
    expose_headers: Optional[List[str]] = None
    max_age: Optional[int] = None


def cors(config: CorsConfig):
    """
    Adds Cross-Origin Resource Sharing support

    :param config: Middleware configration
    """
    if isinstance(config.allow_origin, list):
        allow_origin = config.allow_origin
    else:
        allow_origin = [config.allow_origin]

    @web.middleware
    async def middleware(request: web.Request, handler):
        is_options = request.method == 'OPTIONS'
        is_preflight = is_options and hdrs.ACCESS_CONTROL_REQUEST_METHOD in request.headers

        if is_preflight:
            response = web.Response()
        else:
            response = await handler(request)

        if hdrs.ORIGIN not in request.headers:
            return response

        headers: MultiDict[str] = MultiDict()

        assert isinstance(allow_origin, list)
        _add_header_values(headers, hdrs.ACCESS_CONTROL_ALLOW_ORIGIN, allow_origin)

        if config.allow_credentials:
            headers[hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS] = 'true'

        if config.expose_headers:
            for header in config.expose_headers:
                headers.add(hdrs.ACCESS_CONTROL_EXPOSE_HEADERS, header)

        if is_options:
            if config.allow_requested_headers:
                requested_headers: List[str] = request.headers.getall(hdrs.ACCESS_CONTROL_REQUEST_HEADERS, [])
                _add_header_values(headers, hdrs.ACCESS_CONTROL_ALLOW_HEADERS, requested_headers)
            else:
                _add_header_values(headers, hdrs.ACCESS_CONTROL_ALLOW_HEADERS, config.allow_headers)
            _add_header_values(headers, hdrs.ACCESS_CONTROL_ALLOW_METHODS, config.allow_methods)
            if config.max_age is not None:
                headers[hdrs.ACCESS_CONTROL_MAX_AGE] = str(config.max_age)

        response.headers.update(headers)

        return response

    return middleware


def _add_header_values(headers: MultiDict, header_name: str, values: Optional[List[str]]):
    if not values:
        return
    for value in values:
        headers.add(header_name, value)
