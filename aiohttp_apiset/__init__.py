from .swagger.router import SwaggerRouter
from .views import ApiSet

try:
    from .version import __version__
except ImportError:
    __version__ = 'dev'
