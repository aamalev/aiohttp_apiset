import asyncio
import json

from aiohttp import web


@asyncio.coroutine
def jsonify(app, handler):
    dumps = app.get('dumps', json.dumps)

    @asyncio.coroutine
    def process(request):
        try:
            response = yield from handler(request)
            if isinstance(response, dict):
                status = response.get('status', 200)
                if not isinstance(status, int):
                    status = 200
                return web.json_response(
                    response, status=status, dumps=dumps)
            elif not isinstance(response, web.StreamResponse):
                return web.json_response(response, dumps=dumps)
            return response
        except web.HTTPException as ex:
            if not isinstance(ex.reason, str):
                return web.json_response(
                    ex.reason, status=ex.status, dumps=dumps)
            elif ex.status > 399:
                return web.json_response(
                    {'error': ex.reason}, status=ex.status, dumps=dumps)
            raise
    return process
