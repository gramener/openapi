from tornado.web import HTTPError
import gramex
import inspect
import json
import numpy as np
import re
from typing import List, get_type_hints
from typing_extensions import Annotated
from textwrap import dedent
from gramex.config import merge
from gramex.transforms import handler, Header
from gramex.transforms.transforms import typelist
from gramex.handlers import BaseHandler

error_codes = {
    '200': {
        'description': 'Successful Response',
        'content': {'application/json': {}}
    },
    '400': {
        'description': 'Bad request',
        'content': {'text/html': {'example': 'Bad request'}}
    },
    '401': {
        'description': 'Not authorized',
        'content': {'text/html': {'example': 'Not authorized'}}
    },
    '403': {
        'description': 'Forbidden',
        'content': {'text/html': {'example': 'Forbidden'}}
    },
    '404': {
        'description': 'Not found',
        'content': {'text/html': {'example': 'Not found'}}
    },
    '500': {
        'description': 'Internal server error',
        'content': {'text/html': {'example': 'Internal server error'}}
    },
}


def url_name(pattern):
    # Spec name is the last URL path that has alphabets
    names = [part for part in pattern.split('/') if any(c.isalnum() for c in part)]
    # Capitalize. url-like_this becomes "Url Like This"
    names = [word.capitalize() for word in re.split(r'[\s\-_]', ' '.join(names))]
    return ' '.join(names)


class OpenAPI(BaseHandler):
    types = {
        str: 'string',
        int: 'integer',
        float: 'number',
        bool: 'boolean',
        None: 'null'
    }

    @classmethod
    def function_spec(cls, function):
        doc = function.__doc__
        signature = inspect.signature(function)
        hints = get_type_hints(function)
        params = []
        spec = {'description': dedent(doc), 'parameters': params}
        for name, param in signature.parameters.items():
            hint = hints.get(name, None)
            typ, is_list = typelist(hints[name]) if hint else (str, False)
            config = {
                'in': 'header' if hint and hint is Header else 'query',
                'name': name,
                'description': getattr(param.annotation, '__metadata__', ('',))[0],
                'schema': {}
            }
            params.append(config)
            # If default is not specific, parameter is required.
            if param.default is inspect.Parameter.empty:
                config['required'] = True
            else:
                config['default'] = param.default
            # JSON Schema uses {type: array, items: {type: integer}} for array of ints.
            # But a simple int is {type: integer}
            if is_list:
                config['schema']['type'] = 'array'
                config['schema']['items'] = {'type': cls.types.get(typ, 'string')}
            else:
                config['schema']['type'] = cls.types.get(typ, 'string'),
        spec['responses'] = error_codes
        return spec

    def get(self):
        # TODO: Set header only if not already set in the configuration.
        # This can be handled in gramex/gramex.yaml as a default configuration.
        # Switch to YAML if a YAML spec is requested
        self.set_header('Content-Type', 'application/json')

        spec = {
          'openapi': '3.0.2',
        }

        # info:
        spec['info'] = self.conf.get('kwargs', {}).get('info', {})

        # servers:
        # TODO: Verify that servers[].url can be a relative URL. Else make it absolute
        spec['servers'] = self.conf.get('kwargs', {}).get('servers', {})

        # paths:
        # Loop through every function and get the default specs
        spec['paths'] = {}
        for key, config in gramex.conf['url'].items():
            # Normalize the pattern, e.g. /./docs -> /docs
            pattern = config['pattern'].replace('/./', '/')
            # TODO: Handle wildcards, e.g. /(.*) -> / with an arg
            info = spec['paths'][pattern] = {
                'get': {
                    'summary': f'{url_name(pattern)}: {config["handler"]}'
                },
            }
            cls = gramex.service.url[key].handler_class
            if config['handler'] == 'FunctionHandler':
                function = cls.info['function']
                fnspec = self.function_spec(function.__func__ or function)
                fnspec['summary'] = f'{url_name(pattern)}: {config["handler"]}'
                default_methods = 'GET POST PUT DELETE PATCH OPTIONS'.split()
                for method in getattr(cls, '_http_methods', default_methods):
                    info[method.lower()] = fnspec
            # User's spec definition overrides our spec definition
            merge(info, cls.conf.get('openapi', {}), mode='overwrite')

        self.write(json.dumps(spec))


@handler
def test_function(li1: List[int],
                  lf1: List[float],
                  li2: Annotated[List[int], 'List of ints'],
                  lf2: Annotated[List[float], 'List of floats'],
                  li3: List[int] = [0],
                  lf3: List[float] = [0.0],
                  l1=[],
                  i1: Annotated[int, 'First value'] = 0,
                  i2: Annotated[int, 'Second value'] = 0,
                  s1: str = 'Total',
                  n1: np.int = 0,
                  n2: np.int64 = 0,
                  h: Header = '',
                  code: int = 200):
    '''
    This is a **Markdown** docstring.
    '''
    if code == 200:
        return json.dumps([li1, li2, li3, lf1, lf2, lf3, l1, i1, i2, s1, h])
    else:
        raise HTTPError(code, reason='Something')
