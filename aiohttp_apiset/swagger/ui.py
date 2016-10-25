import os
from functools import lru_cache

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
STATIC = os.path.join(BASE_DIR, 'aiohttp_apiset', 'static')
STATIC_UI = os.path.join(STATIC, 'swagger-ui')
TEMPLATES = os.path.join(BASE_DIR, 'aiohttp_apiset', 'templates')
TEMPLATE_UI = os.path.join(TEMPLATES, 'swagger-ui', 'index.html')


@lru_cache()
def get_template():
    with open(TEMPLATE_UI) as f:
        return f.read()


def rend_template(url):
    template = get_template()
    return template.replace('{{url}}', url)
