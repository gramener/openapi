import json
import gramex
from gramex.handlers import BaseHandler


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
            # TODO: Normalize the pattern, e.g. /./docs -> /docs
            # TODO: Handle wildcards, e.g. /(.*) -> / with an arg
            spec['paths'][config['pattern']] = {
              'summary': '...',
              'description': '...',
              'get': {}
            }
            if config['handler'] == 'FunctionHandler':
                # TODO: Get docstring from here
                print(gramex.service.url[key].handler_class.info['function'].__doc__)

        # TODO: Deep merge the defaults

        self.write(json.dumps(spec))


def test_function(handler):
    '''
    This is a **Markdown** docstring.
    '''
    return 'OK'
