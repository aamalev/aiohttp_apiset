"""Swagger UI and Redoc installer

Author: Alexander Malev
"""
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path


FAKE_UI = os.environ.get('FAKE_UI')

DIR = Path(__file__).parent
PACKAGE_NAME = os.environ.get('PACKAGE', 'aiohttp_apiset')

BASE_STATIC_DIR = DIR / PACKAGE_NAME / 'static'
BASE_TEMPLATES_DIR = DIR / PACKAGE_NAME / 'templates'

SWAGGER_STATIC_DIR = BASE_STATIC_DIR / 'swagger-ui'
SWAGGER_TEMPLATES_DIR = BASE_TEMPLATES_DIR / 'swagger-ui'
SWAGGER_UI_VERSIONS = [
    '2.2.10',
    '3.52.5',
    '4.12.0'
]
SWAGGER_UI_URL = 'https://github.com/swagger-api/swagger-ui/archive/v{}.zip'
SWAGGER_UI_STATIC_PREFIX = '{{static_prefix}}'
SWAGGER_UI_REPLACE_STRINGS = [
    ('http://petstore.swagger.io/v2/swagger.json', '{{url}}'),
    ('https://petstore.swagger.io/v2/swagger.json', '{{url}}'),
    ('href="images', 'href="' + SWAGGER_UI_STATIC_PREFIX + 'images'),
    ('src="images', 'src="' + SWAGGER_UI_STATIC_PREFIX + 'images'),
    ("href='css", "href='" + SWAGGER_UI_STATIC_PREFIX + 'css'),
    ("src='lib", "src='" + SWAGGER_UI_STATIC_PREFIX + 'lib'),
    ("src='swagger-ui.js", "src='" + SWAGGER_UI_STATIC_PREFIX + 'swagger-ui.min.js'),
    ('href="./', 'href="' + SWAGGER_UI_STATIC_PREFIX),
    ('src="./', 'src="' + SWAGGER_UI_STATIC_PREFIX),
    ('href="index.css"', 'href="' + SWAGGER_UI_STATIC_PREFIX + 'index.css"'),
]

REDOC_STATIC_DIR = BASE_STATIC_DIR / 'redoc'
REDOC_TEMPLATES_DIR = BASE_TEMPLATES_DIR / 'redoc'
REDOC_VERSION = 'v2.0.0-rc.70'
REDOC_URL = 'https://cdn.redoc.ly/redoc/{}/bundles/redoc.standalone.js'.format(REDOC_VERSION)
REDOC_TEMPLATE = """
<!DOCTYPE html>
<html>
  <head>
    <title>Redoc</title>
    <!-- needed for adaptive design -->
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <!--
    Redoc doesn't change outer page styles
    -->
    <style>
      body {
        margin: 0;
        padding: 0;
      }
    </style>
  </head>
  <body>
    <redoc spec-url='{{url}}'></redoc>
    <script src="{{static_prefix}}redoc.standalone.js"></script>
  </body>
</html>
"""

SETUP_DIRS = [
    SWAGGER_STATIC_DIR,
    SWAGGER_TEMPLATES_DIR,
    REDOC_STATIC_DIR,
    REDOC_TEMPLATES_DIR
]


def setup_swagger_ui(version):
    version_major = version.split('.')[0]
    template_dir = SWAGGER_TEMPLATES_DIR / version_major
    static_dir = SWAGGER_STATIC_DIR / version_major
    template_ui = template_dir / 'index.html'
    if FAKE_UI:
        os.makedirs(static_dir)
        os.makedirs(template_dir)
        with template_ui.open('w'):
            return
    with tempfile.NamedTemporaryFile() as f:
        url = SWAGGER_UI_URL.format(version)
        with urllib.request.urlopen(url) as r:
            f.write(r.read())
        f.flush()
        with tempfile.TemporaryDirectory() as d:
            with zipfile.ZipFile(f.name) as z:
                mask = 'swagger-ui-{}/dist'.format(version)
                for member in z.namelist():
                    if member.startswith(mask):
                        z.extract(member, path=d)
            shutil.move(os.path.join(d, mask), static_dir)

    if not template_dir.exists():
        os.makedirs(template_dir)

    initializer_path = static_dir / 'swagger-initializer.js'
    if initializer_path.is_file():
        with open(initializer_path) as source:
            init_script = source.read()
    else:
        init_script = None

    with (static_dir / 'index.html').open('rt') as source:
        s = source.read()

    if init_script is not None:
        s = s.replace(
            '<script src="./swagger-initializer.js" charset="UTF-8"> </script>',
            '<script type="text/javascript">' + init_script + '</script>'
        )

    for target, source in SWAGGER_UI_REPLACE_STRINGS:
        s = s.replace(target, source)

    with template_ui.open('wt') as f:
        f.write(s)


def setup_redoc():
    with open(REDOC_TEMPLATES_DIR / 'index.html', 'w') as target:
        target.write(REDOC_TEMPLATE)
    if FAKE_UI:
        return
    with tempfile.NamedTemporaryFile() as f:
        with urllib.request.urlopen(REDOC_URL) as r:
            f.write(r.read())
        f.flush()
        shutil.copy(f.name, REDOC_STATIC_DIR / 'redoc.standalone.js')


def setup():
    for path in SETUP_DIRS:
        if not path.exists():
            os.makedirs(path)
    for swagger_ui_version in SWAGGER_UI_VERSIONS:
        setup_swagger_ui(swagger_ui_version)
    setup_redoc()


def delete():
    for path in SETUP_DIRS:
        if path.exists():
            shutil.rmtree(path)


def is_set():
    return all(i.exists() for i in SETUP_DIRS)


def main():
    if 'delete' in sys.argv:
        delete()
    else:
        setup()


if __name__ == '__main__':
    main()
