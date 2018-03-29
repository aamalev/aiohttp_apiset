from pathlib import Path

from aiohttp import web, hdrs
from aiohttp_apiset import SwaggerRouter
from aiohttp_apiset.middlewares import jsonify


BASE = Path(__file__).parent

router = SwaggerRouter(
    swagger_ui='/swagger/',
    search_dirs=[BASE],
)
router.add_post('/api/v1/doc/{doc_id:\d+}', handler='handlers.set_document')

app = web.Application(
    router=router,
    middlewares=[jsonify],
)
router.set_cors(app, domains='*', headers=(
    (hdrs.ACCESS_CONTROL_EXPOSE_HEADERS, hdrs.AUTHORIZATION),
))

# Include our specifications in a router
router.include(spec='swagger.yaml', basePath='/api/v1')


if __name__ == '__main__':
    # now available swagger-ui to the address http://localhost:8080/swagger/
    web.run_app(app)
