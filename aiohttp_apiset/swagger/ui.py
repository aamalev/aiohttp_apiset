from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
STATIC = BASE_DIR / 'static'
STATIC_UI = STATIC / 'swagger-ui'
TEMPLATES = BASE_DIR / 'templates'
TEMPLATE_UI = {
    2: TEMPLATES / 'swagger-ui' / '2' / 'index.html',
    3: TEMPLATES / 'swagger-ui' / '3' / 'index.html',
}


@lru_cache()
def get_template(version=2):
    with TEMPLATE_UI[version].open() as f:
        return f.read()


def rend_template(url, prefix='', version=2):
    template = get_template(version)
    prefix += str(version) + '/'
    template = template.replace('{{url}}', url)
    return template.replace('{{static_prefix}}', prefix)
