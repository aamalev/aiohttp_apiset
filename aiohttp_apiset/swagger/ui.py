import os
from functools import lru_cache

directory = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
static = os.path.join(directory, 'aiohttp_apiset', 'static')
static_ui = os.path.join(static, 'swagger-ui')
templates = os.path.join(directory, 'aiohttp_apiset', 'templates')


@lru_cache()
def get_template():
    template = os.path.join(templates, 'swagger-ui', 'index.html')
    with open(template) as f:
        return f.read()


def rend_template(url):
    template = get_template()
    return template.replace('{{url}}', url)
