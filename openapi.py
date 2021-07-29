import re
import json
import gramex
import inspect
from typing import List, get_type_hints
from typing_extensions import Annotated
from textwrap import dedent
from gramex.transforms import handler
from gramex.transforms.transforms import typelist
from gramex.handlers import BaseHandler


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
                hints = get_type_hints(function.__func__ or function)
                info['get'].setdefault('description', dedent(doc))
                params = []
                info['get'].setdefault('parameters', params)
                for name, param in signature.parameters.items():
                    # if name in ('i1', 'l1'):
                    #     import ipdb; ipdb.set_trace()
                    default = '' if param.default is inspect.Parameter.empty else param.default
                    typ, is_list = typelist(hints[name]) if name in hints else (str, False)
                    config = {
                        # TODO: [*] Allow header parameters
                        'in': 'query',
                        'name': name,
                        'description': getattr(param.annotation, '__metadata__', ('',))[0],
                        'required': param.default is inspect.Parameter.empty,
                        # TODO: Get schema from param.annotation
                        'schema': {
                            'default': default,
                            'type': 'array' if is_list else self.types.get(typ, 'string'),

                            # 'title': 'Fromdate',
                            # 'description': 'From date in yyyy-mm-dd format'
                        }
                    }
                    if is_list:
                        config['schema']['items'] = {'type': self.types.get(typ, 'string')}
                    params.append(config)
                # TODO: Automate error responses
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
