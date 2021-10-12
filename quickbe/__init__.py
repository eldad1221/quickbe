import os
import uuid
from psutil import Process
from waitress import serve
from datetime import datetime
from cerberus import Validator
import quickbe.logger as b_logger
from inspect import getfullargspec
from pkg_resources import working_set
from quickbe.utils import generate_token
from flask.wrappers import Response, Request
from flask import Flask, request, make_response


def remove_prefix(s: str, prefix: str) -> str:
    if s.startswith(prefix):
        return s.replace(prefix, '', 1)
    else:
        return s


def remove_suffix(s: str, suffix: str) -> str:
    if s.endswith(suffix):
        return s[:(len(suffix)*-1)]
    else:
        return s


def get_env_var(key: str, default: str = None) -> str:
    return os.getenv(key=key, default=default)


def get_env_var_as_int(key: str, default: int = 0) -> int:
    value = get_env_var(key=key)
    try:
        default = int(default)
        value = int(float(value))
    except TypeError:
        value = default
    return value


WEB_SERVER_ENDPOINTS = {}
WEB_SERVER_ENDPOINTS_VALIDATIONS = {}
QUICKBE_WAITRESS_THREADS = get_env_var_as_int('QUICKBE_WAITRESS_THREADS', 10)


def _endpoint_function(path: str):
    if path in WEB_SERVER_ENDPOINTS:
        return WEB_SERVER_ENDPOINTS.get(path)
    else:
        raise NotImplementedError(f'No implementation for path /{path}.')


def _endpoint_validator(path: str) -> Validator:
    if path in WEB_SERVER_ENDPOINTS_VALIDATIONS:
        return WEB_SERVER_ENDPOINTS_VALIDATIONS.get(path)
    else:
        return None


def endpoint(path: str = None, validation: dict = None):

    def decorator(func):
        global WEB_SERVER_ENDPOINTS
        global WEB_SERVER_ENDPOINTS_VALIDATIONS
        if path is None:
            web_path = str(func.__qualname__).lower().replace('.', '/')
        else:
            web_path = path
        if _is_valid_http_handler(func=func):
            Log.debug(f'Registering endpoint: Path={web_path}, Function={func.__qualname__}')
            if web_path in WEB_SERVER_ENDPOINTS:
                raise FileExistsError(f'Endpoint {web_path} already exists.')
            WEB_SERVER_ENDPOINTS[web_path] = func
            if isinstance(validation, dict):
                validator = Validator(validation)
                validator.allow_unknown = True
                WEB_SERVER_ENDPOINTS_VALIDATIONS[web_path] = validator
            return func

    return decorator


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


class HttpSession:

    def __init__(self, req: Request, resp: Response):
        self._request = req
        self._response = resp
        self._data = {}
        if req.json is not None:
            self._data.update(req.json)
        if req.values is not None:
            self._data.update(req.values)

    @property
    def request(self) -> Request:
        return self._request

    @property
    def response(self) -> Response:
        return self._response

    def get_parameter(self, name: str):
        return self._data.get(name)


class WebServer:

    ACCESS_KEY = get_env_var('QUICKBE_WEB_SERVER_ACCESS_KEY', generate_token())
    STOPWATCH_ID = None
    _requests_stack = []
    web_filters = []
    app = Flask(__name__)
    _process = Process(os.getpid())

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
        except Exception:
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
        return {'status': 'OK', 'timestamp': f'{datetime.now()}'}

    @staticmethod
    @app.route(f'/<access_key>/status', methods=['GET'])
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
    @app.route(f'/<access_key>/info', methods=['GET'])
    def web_server_info(access_key):
        def do():
            return {
                'endpoints': list(WEB_SERVER_ENDPOINTS.keys()),
                'packages': sorted([f"{pkg.key}=={pkg.version}" for pkg in working_set]),
            }
        return WebServer._validate_access_key(func=do, access_key=access_key)

    @staticmethod
    @app.route(f'/<access_key>/set_log_level/<level>', methods=['GET'])
    def web_server_set_log_level(access_key, level: int):
        def do():
            Log.set_log_level(level=int(level))
            return f'Log level is now {Log.get_log_level_name()}', 200
        return WebServer._validate_access_key(func=do, access_key=access_key)

    @staticmethod
    @app.route('/favicon.ico', methods=['GET'])
    def favicon():
        return ''

    @staticmethod
    @app.route('/<path>', methods=['GET', 'POST'])
    def dynamic_get(path: str):
        WebServer._register_request()
        resp = make_response()
        session = HttpSession(req=request, resp=resp)
        session.response.status = 200
        for web_filter in WebServer.web_filters:
            http_status = web_filter(session)
            if http_status != 200:
                return session.response, http_status
        req_body = request.json
        if req_body is None:
            req_body = {}
        req_body.update(request.values)
        Log.debug(f'Endpoint /{path}: {req_body}')
        validator = _endpoint_validator(path=path)
        if validator is not None:
            if not validator.validate(req_body):
                return validator.errors, 400
        try:
            resp_data = _endpoint_function(path=path)(session)
            http_status = session.response.status
            resp_headers = resp.headers
            if resp_data is None:
                resp_data = session.response
            if isinstance(resp_data, dict):
                resp_headers['Content-Type'] = 'application/json'
            return resp_data, http_status, resp_headers
        except NotImplementedError as ex:
            Log.debug(f'Error: {ex}')
            return str(ex), 404

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
    def start(host: str = '0.0.0.0', port: int = 8888, threads: int = QUICKBE_WAITRESS_THREADS):
        WebServer.STOPWATCH_ID = Log.start_stopwatch('Quickbe web server is starting...', print_it=True)
        Log.info(f'Server access key: {WebServer.ACCESS_KEY}')
        serve(app=WebServer.app, host=host, port=port, threads=threads)


class Log:

    _stopwatches = {}
    _warning_msgs_count = 0
    _error_msgs_count = 0
    _critical_msgs_count = 0

    @staticmethod
    def set_log_level(level: int):
        b_logger.set_log_level(level=level)

    @staticmethod
    def get_log_level() -> int:
        return b_logger.get_log_level()

    @staticmethod
    def get_log_level_name() -> str:
        return b_logger.get_log_level_name()

    @staticmethod
    def debug(msg: str):
        b_logger.log_msg(level=10, message=msg, current_run_level=3)

    @staticmethod
    def info(msg: str):
        b_logger.log_msg(level=20, message=msg, current_run_level=3)

    @staticmethod
    def warning(msg: str):
        Log._warning_msgs_count += 1
        b_logger.log_msg(level=30, message=msg, current_run_level=3)

    @staticmethod
    def error(msg: str):
        Log._error_msgs_count += 1
        b_logger.log_msg(level=40, message=msg, current_run_level=3)

    @staticmethod
    def critical(msg: str):
        Log._critical_msgs_count += 1
        b_logger.log_msg(level=50, message=msg, current_run_level=3)

    @staticmethod
    def exception(msg: str):
        b_logger.log_exception(message=msg)
        # Log._critical_msgs_count += 1
        # b_logger.log_msg(level=50, message=msg, current_run_level=3)

    @staticmethod
    def warning_count() -> int:
        return Log._warning_msgs_count

    @staticmethod
    def error_count() -> int:
        return Log._error_msgs_count

    @staticmethod
    def critical_count() -> int:
        return Log._critical_msgs_count

    @staticmethod
    def start_stopwatch(msg: str, print_it: bool = False) -> str:
        stopwatch_id = str(uuid.uuid4())
        Log._stopwatches[stopwatch_id] = [datetime.now(), msg]
        if print_it:
            b_logger.log_msg(
                level=10,
                message=f'Start stopwatch: {msg}\t id={stopwatch_id}',
                current_run_level=3
            )
        return stopwatch_id

    @staticmethod
    def stopwatch_seconds(stopwatch_id: str, print_it: bool = True) -> float:
        if stopwatch_id in Log._stopwatches:
            start_time, msg = Log._stopwatches[stopwatch_id]
            time_delta = datetime.now() - start_time
            seconds = time_delta.total_seconds()
            if print_it:
                b_logger.log_msg(
                    level=10,
                    message=f'{seconds} seconds from start, {Log._stopwatches[stopwatch_id][1]}.',
                    current_run_level=3
                )
            return seconds
        else:
            return -1

    @staticmethod
    def stop_stopwatch(stopwatch_id: str, print_it: bool = False) -> bool:
        if stopwatch_id in Log._stopwatches:
            start_time, msg = Log._stopwatches[stopwatch_id]
            if print_it:
                seconds = Log.stopwatch_seconds(stopwatch_id=stopwatch_id, print_it=False)
                b_logger.log_msg(
                    level=10,
                    message=f'{msg} took {seconds} seconds.',
                    current_run_level=3
                )
            try:
                del Log._stopwatches[stopwatch_id]
            except KeyError:
                pass
            return True
        else:
            return False
