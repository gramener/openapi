import re
import json
import gramex
from textwrap import dedent
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
                doc = gramex.service.url[key].handler_class.info['function'].__doc__
                info['get'].setdefault('description', dedent(doc))

        # TODO: Deep merge the defaults
        self.write(json.dumps(spec))


def test_function(handler):
    '''
    This is a **Markdown** docstring.
    '''
    return 'OK'
