from pathlib import Path

from aiohttp import hdrs, web

from aiohttp_apiset import Config, setup
from aiohttp_apiset.middlewares import CorsConfig, cors, jsonify
from aiohttp_apiset.openapi.loader.v2_0 import Loader


BASE = Path(__file__).parent
loader = Loader()
loader.add_directory(BASE)
loader.load('swagger.yaml')
config = Config(
    loader=loader,
    route_base_path='/api/v1',
    ui_path='/swagger/'
)
config.add_operation('POST', r'/api/v1/doc/{doc_id:\d+}', handler='handlers.set_document')
app = web.Application(middlewares=[
    cors(CorsConfig(allow_headers=[hdrs.AUTHORIZATION])),
    jsonify()
])
setup(config, app)

if __name__ == '__main__':
    # now available swagger-ui to the address http://localhost:8080/swagger/
    web.run_app(app)
