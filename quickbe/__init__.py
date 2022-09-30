import os
from quickbelog import Log
from psutil import Process
from datetime import datetime
from inspect import getfullargspec
from pkg_resources import working_set
from quickbe.utils import generate_token
import quickbeserverless as qb_serverless
from flask import Flask, request


class HttpSession(qb_serverless.HttpSession):
    pass


def endpoint(path: str = None, validation: dict = None):

    return qb_serverless.endpoint(path=path, validation=validation)


def _is_valid_http_handler(func) -> bool:
    args_spec = getfullargspec(func=func)
    try:
        args_spec.annotations.pop('return')
    except KeyError:
        pass
    arg_types = args_spec.annotations.values()
    if len(arg_types) == 1 and HttpSession in arg_types:
        return True
    else:
        error_msg = f'Function {func.__qualname__} needs one argument, type ' \
                    f'{HttpSession.__qualname__}.Got spec: {args_spec}'
        Log.error(error_msg)
        raise TypeError(error_msg)


EVENT_BODY_KEY = 'body'
EVENT_HEADERS_KEY = 'headers'
EVENT_QUERY_STRING_KEY = 'queryStringParameters'


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
    @app.route('/<path>', methods=['GET', 'POST'])
    def dynamic_get(path: str):
        WebServer._register_request()
        session = HttpSession(body=request.json, parameters=request.args, headers=request.headers)
        for web_filter in WebServer.web_filters:
            http_status = web_filter(session)
            if http_status != 200:
                return 'Error', http_status
        response_body, response_headers, status_code = qb_serverless.execute_endpoint(
            path=path,
            body=request.json,
            parameters=request.args,
            headers=request.headers
        )
        return response_body, status_code, response_headers

    @staticmethod
    def add_filter(func):
        """
        Add a function as a web filter. Function must receive request and return int as http status.
        If returns 200 the request will be processed otherwise it will stop and return this status
        :param func:
        :return:
        """
        if hasattr(func, '__call__') and _is_valid_http_handler(func=func):
            WebServer.web_filters.append(func)
            Log.info(f'Filter {func.__qualname__} added.')
        else:
            raise TypeError(f'Filter is not a function, got {type(func)} instead.')

    @staticmethod
    def start(host: str = '0.0.0.0', port: int = 8888):
        WebServer.STOPWATCH_ID = Log.start_stopwatch('Quickbe web server is starting...', print_it=True)
        WebServer.app.run(host=host, port=port)
