#!/usr/bin/env python
""" Installer swagger-ui

Author: Alexander Malev
"""

import urllib.request
import tempfile
import zipfile
import shutil
import os
import sys

VERSION = os.environ.get('SWAGGER_UI_VERSION', '2.2.10')
PACKAGE = os.environ.get('PACKAGE', 'aiohttp_apiset')

URL = 'https://github.com/swagger-api/swagger-ui/archive/v{}.zip'
DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.join(DIR, PACKAGE, 'static', 'swagger-ui')
TEMPLATES_DIR = os.path.join(DIR, PACKAGE, 'templates', 'swagger-ui')

PREFIX = '{{static_prefix}}'
REPLACE_STRINGS = [
    ('http://petstore.swagger.io/v2/swagger.json', '{{url}}'),
    ('https://petstore.swagger.io/v2/swagger.json', '{{url}}'),
    ('href="images', 'href="' + PREFIX + 'images'),
    ('src="images', 'src="' + PREFIX + 'images'),
    ("href='css", "href='" + PREFIX + 'css'),
    ("src='lib", "src='" + PREFIX + 'lib'),
    ("src='swagger-ui.js", "src='" + PREFIX + 'swagger-ui.min.js'),
    ('href="./', 'href="' + PREFIX),
    ('src="./', 'src="' + PREFIX),
]


def setup_ui(version=VERSION):
    template_dir = os.path.join(TEMPLATES_DIR, version[0])
    static_dir = os.path.join(STATIC_DIR, version[0])
    template_ui = os.path.join(template_dir, 'index.html')
    if os.environ.get('FAKE_UI'):
        os.makedirs(static_dir)
        os.makedirs(template_dir)
        with open(template_ui, 'w'):
            return
    with tempfile.NamedTemporaryFile() as f:
        with urllib.request.urlopen(URL.format(version)) as r:
            f.write(r.read())
        f.flush()
        with tempfile.TemporaryDirectory() as d:
            with zipfile.ZipFile(f.name) as z:
                mask = 'swagger-ui-{}/dist'.format(version)
                for member in z.namelist():
                    if member.startswith(mask):
                        z.extract(member, path=d)
            shutil.move(os.path.join(d, mask), static_dir)

    if not os.path.exists(template_dir):
        os.makedirs(template_dir)

    with open(os.path.join(static_dir, 'index.html'), 'rt') as source:
        s = source.read()
    for target, source in REPLACE_STRINGS:
        s = s.replace(target, source)
    with open(template_ui, 'wt') as f:
        f.write(s)


def delete():
    shutil.rmtree(TEMPLATES_DIR)
    shutil.rmtree(STATIC_DIR)


if __name__ == '__main__':
    if 'delete' in sys.argv:
        delete()
    else:
        setup_ui()
