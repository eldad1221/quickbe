import os
import json
from quickbelog import Log
from psutil import Process
from datetime import datetime
from pkg_resources import working_set
from quickbe.utils import generate_token
import quickbeserverless as qb_serverless
from flask import Flask, request


class HttpSession(qb_serverless.HttpSession):

    def __init__(self, body: dict = None, parameters: dict = None, headers: dict = None):
        self._user_id = None
        super().__init__(body=body, parameters=parameters, headers=headers)

    @property
    def user_id(self) -> str:
        return self._user_id

    def set_user_id(self, user_id: str):
        self._user_id = user_id


def endpoint(path: str = None, validation: dict = None, doc: str = None, example=None):
    """
    Endpoint decorator
    :param path: Web path (route) to map
    :param validation: Validation schema, check this for more info https://docs.python-cerberus.org/en/stable/
    :param doc: Documentation text
    :param example: Example for function response
    :return:
    """

    return qb_serverless.endpoint(path=path, validation=validation, doc=doc, example=example)


EVENT_BODY_KEY = 'body'
EVENT_HEADERS_KEY = 'headers'
EVENT_QUERY_STRING_KEY = 'queryStringParameters'
QUICKBE_DEV_MODE_KEY = 'QUICKBE_DEV_MODE'


class WebServer:

    ACCESS_KEY = os.getenv('QUICKBE_WEB_SERVER_ACCESS_KEY', generate_token())
    STOPWATCH_ID = None
    _requests_stack = []
    web_filters = []
    app = Flask(__name__)
    _process = Process(os.getpid())
    Log.info(f'Server access key: {ACCESS_KEY}')

    @staticmethod
    def _register_request():
        WebServer._requests_stack.append(datetime.now().timestamp())
        if len(WebServer._requests_stack) > 100:
            WebServer._requests_stack.pop(0)

    @staticmethod
    def requests_per_minute() -> float:
        try:
            delta = datetime.now().timestamp() - WebServer._requests_stack[0]
            return len(WebServer._requests_stack) * 60 / delta
        except (ZeroDivisionError, IndexError, ValueError):
            return 0

    @staticmethod
    def _validate_access_key(func, access_key: str):
        if access_key == WebServer.ACCESS_KEY:
            return func()
        else:
            return 'Unauthorized', 401

    @staticmethod
    @app.route('/health', methods=['GET'])
    def health():
        """
        Health check endpoint
        :return:
        Return 'OK' and time stamp to ensure that response is not cached by any proxy.
        {"status":"OK","timestamp":"2021-10-24 15:06:37.746497"}

        You may pass HTTP parameter `echo` and it will include it in the response.
        {"echo":"Testing","status":"OK","timestamp":"2021-10-24 15:03:45.830066"}
        """
        data = {'status': 'OK', 'timestamp': f'{datetime.now()}'}
        echo_text = request.args.get('echo')
        if echo_text is not None:
            data['echo'] = echo_text
        return data

    @staticmethod
    @app.route(f'/<access_key>/quickbe-server-status', methods=['GET'])
    def web_server_status(access_key):
        def do():
            return {
                'status': 'OK',
                'timestamp': f'{datetime.now()}',
                'log_level': Log.get_log_level_name(),
                'log_warning_count': Log.warning_count(),
                'log_error_count': Log.error_count(),
                'log_critical_count': Log.critical_count(),
                'memory_utilization': WebServer._process.memory_info().rss/1024**2,
                'requests_per_minute': WebServer.requests_per_minute(),
                'uptime_seconds': Log.stopwatch_seconds(stopwatch_id=WebServer.STOPWATCH_ID, print_it=False)
            }
        return WebServer._validate_access_key(func=do, access_key=access_key)

    @staticmethod
    @app.route(f'/<access_key>/quickbe-server-info', methods=['GET'])
    def web_server_info(access_key):
        def do():
            return {
                'endpoints': list(qb_serverless.WEB_SERVER_ENDPOINTS.keys()),
                'packages': sorted([f"{pkg.key}=={pkg.version}" for pkg in working_set]),
            }
        return WebServer._validate_access_key(func=do, access_key=access_key)

    @staticmethod
    @app.route(f'/<access_key>/quickbe-server-environ', methods=['GET'])
    def web_server_get_environ(access_key):
        def do():
            return dict(os.environ)
        return WebServer._validate_access_key(func=do, access_key=access_key)

    @staticmethod
    @app.route(f'/<access_key>/set_log_level/<level>', methods=['GET'])
    def web_server_set_log_level(access_key, level: int):
        def do():
            Log.set_log_level(level=int(level))
            return f'Log level is now {Log.get_log_level_name()}', 200
        return WebServer._validate_access_key(func=do, access_key=access_key)

    @staticmethod
    def _schema_documentation(schema: dict, prefix: str = '') -> str:
        """
        Generate documentation by schema
        :param schema:
        :param prefix:
        :return: doc string
        """
        html = ''
        for name, value in schema.items():
            html += f'<tr><td><b>{prefix}{name}</b>'
            if value.get('required', False):
                html += ' *required'
            html += f'</td> <td>{value.get("type", "string")}</td>'
            html += f'<td>{value.get("doc", "")}'
            if 'default' in value:
                html += f'<br>Default: <b>{value.get("default")}</b>'
            if 'allowed' in value:
                html += f'<br>Allowed: <b>{", ".join([str(item) for item in value.get("allowed")])}</b>'
            if 'min' in value:
                html += f'<br>Minimum: <b>{value.get("min")}</b>'
            if 'max' in value:
                html += f'<br>Maximum: <b>{value.get("max")}</b>'
            if 'example' in value:
                html += f'<br>Example: <b>{value.get("example")}</b>'
            html += f'</td></tr>'
            if value.get("type") == 'dict':
                html += WebServer._schema_documentation(schema=value.get("schema"), prefix=f'{prefix}{name}.')
        return html

    @staticmethod
    @app.route(f'/quickbe-endpoint-doc/<path>', methods=['GET'])
    def web_server_get_endpoint_doc(path: str):
        def do():
            try:
                if path not in qb_serverless.WEB_SERVER_ENDPOINTS:
                    raise KeyError(f'No implementation for {path}.')

                validator_schema = qb_serverless.get_endpoint_validator(path=path)
                html = f'<html><body><h2>Path: /{path}</h2>{qb_serverless.WEB_SERVER_ENDPOINTS_DOCS.get(path, "")}'

                if validator_schema:
                    html += '<h3>Parameters</h3><table cellpadding="10">' \
                            '<tr><th>Name</td><th>Type</td><th>Description</td></tr>'
                    schema = validator_schema.root_schema.schema
                    html += f'{WebServer._schema_documentation(schema=schema)}</table>'

                if path in qb_serverless.WEB_SERVER_ENDPOINTS_EXAMPLE_RESPONSES:
                    example_response = qb_serverless.WEB_SERVER_ENDPOINTS_EXAMPLE_RESPONSES.get(path)
                    html += f'<h3>Response</h3><pre>{json.dumps(example_response, indent=4)}</pre>'

                html += '</body></html>'
                return html, 200
            except Exception as e:
                msg = f'Can not generate endpoint documentation, {e.__class__.__name__}: {e}'
                Log.warning(msg=msg)
                raise e
        try:
            if os.getenv(QUICKBE_DEV_MODE_KEY, '').lower().strip() in ['1', 'true', 'y', 'yes']:
                return do()
        except (AttributeError, KeyError):
            pass
        return 'File not found', 404

    @staticmethod
    @app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
    @app.route('/<path:path>', methods=['GET', 'POST'])
    def dynamic_get(path: str):
        WebServer._register_request()
        session = HttpSession(body=request.json, parameters=request.args, headers=request.headers)
        for web_filter in WebServer.web_filters:
            resp = web_filter(session)
            if session.response_status != 200:
                return resp, session.response_status
        response_headers = {}
        try:
            response_body, response_headers, status_code = qb_serverless.execute_endpoint_with_session(
                path=path,
                session=session
            )
        except NotImplementedError as e:
            status_code = 404
            response_body = 'File not found'
        except Exception as e:
            status_code = 500
            response_body = f'{e}'
        return response_body, status_code, response_headers

    @staticmethod
    def add_filter(func):
        """
        Add a function as a web filter. Function must receive request and return int as http status.
        If returns 200 the request will be processed otherwise it will stop and return this status
        :param func:
        :return:
        """
        if hasattr(func, '__call__') and qb_serverless.is_valid_http_handler(func=func):
            WebServer.web_filters.append(func)
            Log.info(f'Filter {func.__qualname__} added.')
        else:
            raise TypeError(f'Filter is not valid! Got this {type(func)}.')

    @staticmethod
    def start(host: str = '0.0.0.0', port: int = 8888):
        WebServer.STOPWATCH_ID = Log.start_stopwatch('Quickbe web server is starting...', print_it=True)
        WebServer.app.run(host=host, port=port)
