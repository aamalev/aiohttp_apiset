import codecs
from setuptools import setup, find_packages
import os
import re


with codecs.open(os.path.join(os.path.abspath(os.path.dirname(
        __file__)), 'aiohttp_apiset', '__init__.py'), 'r', 'latin1') as fp:
    try:
        version = re.findall(r"^__version__ = '([^']+)'$", fp.read(), re.M)[0]
    except IndexError:
        raise RuntimeError('Unable to determine version.')


def read(f):
    return open(os.path.join(os.path.dirname(__file__), f)).read().strip()

install_requires = ['aiohttp>=0.21', 'pyyaml']
tests_require = ['pytest',
                 'pytest-asyncio',
                 'pytest-cov',
                 'pytest-pep8']


setup(name='aiohttp_apiset',
      version=version,
      description=("scafold for make api on aiohttp.web"),
      classifiers=[
          'License :: OSI Approved :: Apache Software License',
          'Intended Audience :: Developers',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Topic :: Internet :: WWW/HTTP'],
      author='Alexander Malev',
      author_email='malev@somedev.ru',
      url='https://github.com/aamalev/aiohttp_apiset/',
      license='Apache 2',
      packages=find_packages(),
      install_requires=install_requires,
      tests_require=tests_require,
      include_package_data=True,
)
