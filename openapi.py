import re
import json
import gramex
import inspect
from typing import List
from typing_extensions import Annotated
from textwrap import dedent
from gramex.transforms import handler
from gramex.handlers import BaseHandler


def url_name(pattern):
    # Spec name is the last URL path that has alphabets
    names = [part for part in pattern.split('/') if any(c.isalnum() for c in part)]
    # Capitalize. url-like_this becomes "Url Like This"
    names = [word.capitalize() for word in re.split(r'[\s\-_]', ' '.join(names))]
    return ' '.join(names)


class OpenAPI(BaseHandler):
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
            if config['handler'] == 'FunctionHandler':
                function = gramex.service.url[key].handler_class.info['function']
                doc = function.__doc__
                signature = inspect.signature(function.__func__ or function)
                info['get'].setdefault('description', dedent(doc))
                for name, param in signature.parameters.items():
                    print(param.default, type(param.default), repr(param.default))
                info['get'].setdefault('parameters', [{
                    'in': 'query',
                    'name': name,
                    'description': getattr(param.annotation, '__metadata__', ('',))[0],
                    'required': param.default is None,
                    # TODO: Get defaults into example
                    # TODO: Get schema from param.annotation
                    'schema': {
                        'title': 'Fromdate',
                        'type': 'string',
                        'description': 'From date in yyyy-mm-dd format'
                    },
                } for name, param in signature.parameters.items()])
                info['get'].setdefault('responses', {
                    '200': {
                        'description': 'Successful Response',
                        'content': {
                            'application/json': {'schema': {}}
                        }
                    },
                    '404': {
                        'description': 'Not found'
                    },
                })

        # TODO: Deep merge the defaults
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
                  s1: str = 'Total'):
    '''
    This is a **Markdown** docstring.
    '''
    return json.dumps([li1, li2, li3, lf1, lf2, lf3, l1, i1, i2, s1])
