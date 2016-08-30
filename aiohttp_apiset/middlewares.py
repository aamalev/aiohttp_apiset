import asyncio

from aiohttp import web


@asyncio.coroutine
def jsonify(app, handler):
    @asyncio.coroutine
    def process(request):
        try:
            response = yield from handler(request)
            if not isinstance(response, web.Response):
                return web.json_response(response)
            elif response.status != 200:
                return web.json_response(
                    {'error': response.message}, status=response.status)
        except web.HTTPException as ex:
            if ex.status != 200:
                return web.json_response(
                    {'error': ex.reason}, status=ex.status)
            raise
    return process
