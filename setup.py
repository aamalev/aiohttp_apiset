from setuptools import setup, find_packages
import os
import re

try:
    import swagger_ui
except ImportError:
    pass
else:
    if not os.path.exists(swagger_ui.STATIC_DIR):
        swagger_ui.setup_ui('2.2.10')
        swagger_ui.setup_ui('3.17.2')


with open(os.path.join(os.path.abspath(os.path.dirname(
        __file__)), 'aiohttp_apiset', '__init__.py'), 'r',
        encoding='latin1') as fp:
    try:
        version = re.findall(r"^__version__ = '([^']+)'$", fp.read(), re.M)[0]
    except IndexError:
        raise RuntimeError('Unable to determine version.')


def read(f):
    path = os.path.join(os.path.dirname(__file__), f)
    return open(path).read().strip()


install_requires = [
    'aiohttp>=1.2,<3.3',
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
    version=version,
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
