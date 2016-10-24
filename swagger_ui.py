import urllib.request
import tempfile
import zipfile
import shutil
import os

VERSION = '2.2.6'

URL = 'https://github.com/swagger-api/swagger-ui/archive/v{}.zip'
d = os.path.dirname(__file__)
static = os.path.join(d, 'aiohttp_apiset', 'static', 'swagger-ui')
templates = os.path.join(d, 'aiohttp_apiset', 'templates', 'swagger-ui')


def setup_ui():
    with urllib.request.urlopen(URL.format(VERSION)) as r, \
            tempfile.NamedTemporaryFile() as f:
        f.write(r.read())
        f.flush()
        with zipfile.ZipFile(f.name) as z, tempfile.TemporaryDirectory() as d:
            mask = 'swagger-ui-{}/dist'.format(VERSION)
            for member in z.namelist():
                if member.startswith(mask):
                    z.extract(member, path=d)
            shutil.move(os.path.join(d, mask), static)

    if not os.path.exists(templates):
        os.makedirs(templates)

    with open(os.path.join(static, 'index.html'), 'rt') as source:
        s = source.read()
    s = s.replace('http://petstore.swagger.io/v2/swagger.json', '{{url}}')
    with open(os.path.join(templates, 'index.html'), 'wt') as f:
        f.write(s)


if __name__ == '__main__':
    setup_ui()
