import os
import json
from quickbelog import Log
from psutil import Process
from datetime import datetime
from cerberus import Validator
from flask import Flask, request
from inspect import getfullargspec
from collections import OrderedDict
from pkg_resources import working_set
from quickbe.utils import generate_token

WEB_SERVER_ENDPOINTS = {}
WEB_SERVER_ENDPOINTS_VALIDATIONS = {}
WEB_SERVER_ENDPOINTS_DOCS = {}
WEB_SERVER_ENDPOINTS_EXAMPLE_RESPONSES = {}


def get_endpoint_validator(path: str) -> Validator:
    if path in WEB_SERVER_ENDPOINTS_VALIDATIONS:
        return WEB_SERVER_ENDPOINTS_VALIDATIONS.get(path)
    else:
        return None


def is_valid_http_handler(func) -> bool:
    args_spec = getfullargspec(func=func)
    try:
        args_spec.annotations.pop('return')
    except KeyError:
        pass
    arg_types = args_spec.annotations.values()
    if len(arg_types) == 1 and issubclass(list(arg_types)[0], HttpSession):
        return True
    else:
        raise TypeError(
            f'Function {func.__qualname__} needs one argument, type {HttpSession.__qualname__}.Got spec: {args_spec}'
        )


def endpoint(path: str = None, validation: dict = None, doc: str = None, example=None):
    """
    Endpoint decorator
    :param path: Web path (route) to map
    :param validation: Validation schema, check this for more info https://docs.python-cerberus.org/en/stable/
    :param doc: Documentation text
    :param example: Example for function response
    :return:
    """

    def decorator(func):
        global WEB_SERVER_ENDPOINTS
        global WEB_SERVER_ENDPOINTS_VALIDATIONS
        global WEB_SERVER_ENDPOINTS_DOCS
        global WEB_SERVER_ENDPOINTS_EXAMPLE_RESPONSES
        if path is None:
            web_path = str(func.__qualname__).lower().replace('.', '/').strip()
        else:
            web_path = path.strip()

        if web_path.startswith('/') and len(web_path) > 0:
            web_path = web_path[1:]

        if is_valid_http_handler(func=func):
            Log.debug(f'Registering endpoint: Path={web_path}, Function={func.__qualname__}')
            if web_path in WEB_SERVER_ENDPOINTS:
                raise FileExistsError(f'Endpoint {web_path} already exists.')

            WEB_SERVER_ENDPOINTS[web_path] = func

            if isinstance(validation, dict):
                validator = EndPointValidator(validation, purge_unknown=True)
                validator.allow_unknown = True
                WEB_SERVER_ENDPOINTS_VALIDATIONS[web_path] = validator

            if doc is not None:
                WEB_SERVER_ENDPOINTS_DOCS[web_path] = doc

            if example is not None:
                WEB_SERVER_ENDPOINTS_EXAMPLE_RESPONSES[web_path] = example
            return func

    return decorator


class EndPointValidator(Validator):

    def _validate_doc(self, constraint, field, value):
        """
        For documentation text
        :param constraint:
        :param field:
        :param value:
        :return:
        """
        pass

    def _validate_example(self, constraint, field, value):
        """
        For example value
        :param constraint:
        :param field:
        :param value:
        :return:
        """
        pass


class HttpSession:

    def __init__(self, body: dict = None, parameters: dict = None, headers: dict = None):
        self._response_status = 200
        self._response_headers = {}
        self._user_id = None

        if body is None:
            body = {}
        self._data = body

        self._headers = headers

        if parameters is not None and isinstance(parameters, dict):
            self._data.update(parameters)

    @property
    def request_headers(self) -> dict:
        return self._headers

    @property
    def data(self) -> dict:
        return self._data

    @property
    def response_status(self) -> int:
        return self._response_status

    @property
    def response_headers(self) -> dict:
        return self._response_headers

    def get(self, name: str, default=None):
        return self._data.get(name, default)

    def set_status(self, status: int):
        self._response_status = status

    def set_response_header(self, key: str, value: str):
        self._response_headers[key] = value

    @property
    def user_id(self) -> str:
        return self._user_id

    def set_user_id(self, user_id: str):
        self._user_id = user_id


QUICKBE_DOCUMENTATION_MODE_KEY = 'QUICKBE_DOCUMENTATION_MODE'
QUICKBE_DEVELOPERS_KEYS_KEY = 'QUICKBE_DEVELOPERS_KEYS'
QUICKBE_WEB_SERVER_ACCESS_KEY = 'QUICKBE_WEB_SERVER_ACCESS_KEY'

DEVKEY_PARAMETER = 'devkey'


class WebServer:

    ACCESS_KEY = os.getenv(QUICKBE_WEB_SERVER_ACCESS_KEY, generate_token())
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
    def is_developer(http_parameters: dict, http_headers) -> bool:
        key = http_parameters.get(DEVKEY_PARAMETER, '')
        for dev_key in os.getenv(QUICKBE_DEVELOPERS_KEYS_KEY, '').split(','):
            dev_key = dev_key.strip()
            if dev_key.startswith(f'{key.strip()}:'):
                dev_name = dev_key.split(':')[1]
                Log.info(f'DEVELOPER ACCESS {dev_name} accessed path {http_headers.environ.get("REQUEST_URI")}')
                return True
        return False

    @staticmethod
    def is_documentation_on(http_parameters: dict, http_headers: dict) -> bool:
        is_dev_mode = os.getenv(QUICKBE_DOCUMENTATION_MODE_KEY, '').lower().strip() in ['1', 'true', 'y', 'yes', 'on']
        return bool(is_dev_mode + WebServer.is_developer(http_parameters=http_parameters, http_headers=http_headers))

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
                'endpoints': list(WEB_SERVER_ENDPOINTS.keys()),
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

    ENDPOINT_DOC_PATH = '/endpoint-doc/'

    @staticmethod
    @app.route(f'/quickbe-endpoint-doc/<path:path>', methods=['GET'])
    @app.route(f'{ENDPOINT_DOC_PATH}<path:path>', methods=['GET'])
    def web_server_get_endpoint_doc(path: str):
        def do():
            try:
                if path not in WEB_SERVER_ENDPOINTS:
                    raise KeyError(f'No implementation for {path}.')

                validator_schema = get_endpoint_validator(path=path)
                html = f'<html><body><h2>Path: /{path}</h2>{WEB_SERVER_ENDPOINTS_DOCS.get(path, "")}'

                if validator_schema:
                    html += '<h3>Parameters</h3><table cellpadding="10">' \
                            '<tr><th>Name</td><th>Type</td><th>Description</td></tr>'
                    schema = validator_schema.root_schema.schema
                    html += f'{WebServer._schema_documentation(schema=schema)}</table>'

                if path in WEB_SERVER_ENDPOINTS_EXAMPLE_RESPONSES:
                    example_response = WEB_SERVER_ENDPOINTS_EXAMPLE_RESPONSES.get(path)
                    html += f'<h3>Response</h3><pre>{json.dumps(example_response, indent=4)}</pre>'

                html += '</body></html>'
                return html, 200
            except Exception as e:
                msg = f'Can not generate endpoint documentation, {e.__class__.__name__}: {e}'
                Log.warning(msg=msg)
                raise e
        try:
            if WebServer.is_documentation_on(http_parameters=request.args, http_headers=request.headers):
                return do()
        except (AttributeError, KeyError):
            pass
        return 'File not found', 404

    @staticmethod
    @app.route(f'/endpoints-index', methods=['GET'])
    @app.route(f'/quickbe-endpoints-index', methods=['GET'])
    def web_server_get_endpoints_index():
        def do():
            html = '<html><title>Endpoints index</title><body><h1>Endpoints Index</h1><div style="margin-left:20px">'
            endpoints_doc = OrderedDict(sorted(WEB_SERVER_ENDPOINTS_DOCS.items()))

            devkey = request.args.get(DEVKEY_PARAMETER, '')
            if devkey != '':
                devkey = f'?{DEVKEY_PARAMETER}={devkey}'

            for path, doc in endpoints_doc.items():
                html += f'<a href="{WebServer.ENDPOINT_DOC_PATH}{path}{devkey}"><h3>{path}</h3></a>'
                html += f'{doc}<br>'
            html += '</div></body></html>'
            return html, 200
        try:
            if WebServer.is_documentation_on(http_parameters=request.args, http_headers=request.headers):
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
            response_body, response_headers, status_code = execute_endpoint_with_session(
                path=path,
                session=session
            )
        except NotImplementedError:
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
        if hasattr(func, '__call__') and is_valid_http_handler(func=func):
            WebServer.web_filters.append(func)
            Log.info(f'Filter {func.__qualname__} added.')
        else:
            raise TypeError(f'Filter is not valid! Got this {type(func)}.')

    @staticmethod
    def start(host: str = '0.0.0.0', port: int = 8888):
        WebServer.STOPWATCH_ID = Log.start_stopwatch('Quickbe web server is starting...', print_it=True)
        WebServer.app.run(host=host, port=port)


def _endpoint_function(path: str):
    if path.startswith('/') and len(path) > 0:
        path = path[1:]
    if path in WEB_SERVER_ENDPOINTS:
        return WEB_SERVER_ENDPOINTS.get(path)
    else:
        raise NotImplementedError(f'No implementation for path /{path}.')


def execute_endpoint(path: str, headers: dict, body: dict, parameters: dict) -> (dict, dict, int):

    session = HttpSession(
        body=body,
        parameters=parameters,
        headers=headers
    )
    return execute_endpoint_with_session(path=path, session=session)


def execute_endpoint_with_session(path: str, session: HttpSession) -> (dict, dict, int):
    validator = get_endpoint_validator(path=path)
    status_code = 200
    resp_body = {}

    if validator is not None:
        if not validator.validate(session.data):
            resp_body = validator.errors
            status_code = 400
        else:
            session._data = validator.normalized(session.data)

    if status_code == 200:
        resp_body = _endpoint_function(path=path)(session)
        status_code = session.response_status

    return resp_body, session.response_headers, status_code


AWS_LAMBDA_EVENT_BODY_KEY = 'body'
AWS_LAMBDA_EVENT_HEADERS_KEY = 'headers'
AWS_LAMBDA_EVENT_QUERY_STRING_KEY = 'queryStringParameters'


def aws_lambda_handler(event: dict, context=None):

    path = event.get('path', '/error')

    if context is not None:
        Log.debug(f'Lambda function: {context.function_name}, path: {path}.')

    body = event.get(AWS_LAMBDA_EVENT_BODY_KEY, '{}')
    try:
        if body is None:
            body = {}
        elif isinstance(body, dict):
            pass
        elif isinstance(body, str):
            body = json.loads(body)
    except (ValueError, TypeError):
        pass

    resp_body, response_headers, status_code = execute_endpoint(
        path=path, headers=event.get(AWS_LAMBDA_EVENT_HEADERS_KEY, {}),
        body=body,
        parameters=event.get(AWS_LAMBDA_EVENT_QUERY_STRING_KEY, {})
    )

    try:
        resp_body = json.dumps(resp_body)
    except ValueError:
        msg = 'Can not convert response body to JSON format.'
        Log.exception(msg)
        resp_body = msg
        status_code = 500

    return {

        "statusCode": status_code,
        AWS_LAMBDA_EVENT_HEADERS_KEY: response_headers,
        AWS_LAMBDA_EVENT_BODY_KEY: resp_body
    }
