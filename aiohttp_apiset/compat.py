import keyword
import re

from aiohttp.abc import AbstractRouter
from aiohttp.web_urldispatcher import \
    AbstractRoute, UrlMappingMatchInfo, MatchInfoError


class CompatRouter(AbstractRouter):
    DYN = re.compile(r'\{(?P<var>[_a-zA-Z][_a-zA-Z0-9]*)\}')
    DYN_WITH_RE = re.compile(
        r'\{(?P<var>[_a-zA-Z][_a-zA-Z0-9]*):(?P<re>.+)\}')
    GOOD = r'[^{}/]+'
    ROUTE_RE = re.compile(r'(\{[_a-zA-Z][^{}]*(?:\{[^{}]*\}[^{}]*)*\})')
    NAME_SPLIT_RE = re.compile(r'[.:-]')

    def __init__(self):
        super().__init__()
        self._app = None
        self._named_resources = {}

    def post_init(self, app):
        assert app is not None
        self._app = app

    def validate_name(self, name: str):
        """
        Fragment aiohttp.web_urldispatcher.UrlDispatcher#_reg_resource
        """
        parts = self.NAME_SPLIT_RE.split(name)
        for part in parts:
            if not part.isidentifier() or keyword.iskeyword(part):
                raise ValueError('Incorrect route name {!r}, '
                                 'the name should be a sequence of '
                                 'python identifiers separated '
                                 'by dash, dot or column'.format(name))
        if name in self._named_resources:
            raise ValueError('Duplicate {!r}, '
                             'already handled by {!r}'
                             .format(name, self._named_resources[name]))

    @classmethod
    def get_pattern_formatter(cls, location):
        """
        Fragment from aiohttp.web_urldispatcher.UrlDispatcher#add_resource
        :param location:
        :return:
        """
        pattern = ''
        formatter = ''
        for part in cls.ROUTE_RE.split(location):
            match = cls.DYN.match(part)
            if match:
                pattern += '(?P<{}>{})'.format(match.group('var'), cls.GOOD)
                formatter += '{' + match.group('var') + '}'
                continue

            match = cls.DYN_WITH_RE.match(part)
            if match:
                pattern += '(?P<{var}>{re})'.format(**match.groupdict())
                formatter += '{' + match.group('var') + '}'
                continue

            if '{' in part or '}' in part:
                raise ValueError("Invalid path '{}'['{}']".format(
                    location, part))

            formatter += part
            pattern += re.escape(part)

        try:
            re.compile(pattern)
        except re.error as exc:
            raise ValueError(
                "Bad pattern '{}': {}".format(pattern, exc)) from None
        return pattern, formatter
