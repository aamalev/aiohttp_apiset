import re
from setuptools import setup, find_packages
from pathlib import Path

try:
    import swagger_ui
except ImportError:
    pass
else:
    if not Path(swagger_ui.STATIC_DIR).exists():
        swagger_ui.setup_ui('2.2.10')
        swagger_ui.setup_ui('3.23.3')


def read(f):
    path = Path(__file__).parent / f
    if not path.exists():
        return ''
    return path.read_text(encoding='latin1').strip()


def get_version():
    text = read('aiohttp_apiset/version.py')
    if not text:
        text = read('aiohttp_apiset/__init__.py')
    try:
        return re.findall(r"^__version__ = '([^']+)'$", text, re.M)[0]
    except IndexError:
        raise RuntimeError('Unable to determine version.')


install_requires = [
    'aiohttp>=2,<3.6',
    'pyyaml',
    'jsonschema',
]

tests_require = [
    'pytest',
    'pytest-aiohttp',
    'pytest-mock',
    'pytest-cov',
    'pytest-pep8',
]


setup(
    name='aiohttp-apiset',
    version=get_version(),
    description='Build routes using swagger specification',
    long_description=read('README.rst') + '\n\n' + read('HISTORY.rst'),
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP'],
    author='Alexander Malev',
    author_email='malev@somedev.ru',
    url='https://github.com/aamalev/aiohttp_apiset/',
    license='Apache 2',
    packages=[i for i in find_packages() if i.startswith('aiohttp_apiset')],
    install_requires=install_requires,
    tests_require=tests_require,
    include_package_data=True,
    extras_require={
        'docs': [
            'sphinx >= 1.4.8',
            'sphinx_rtd_theme']},
)
