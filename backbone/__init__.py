import os
import uuid
from waitress import serve
from datetime import datetime
from cerberus import Validator
from inspect import getfullargspec
from flask.wrappers import Response, Request
from flask import Flask, request, make_response
import backbone.logger as b_logger


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
BACKBONE_WAITRESS_THREADS = get_env_var_as_int('BACKBONE_WAITRESS_THREADS', 10)


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

    @property
    def request(self) -> Request:
        return self._request

    @property
    def response(self) -> Response:
        return self._response

    def get_parameter(self, name: str):
        return self.request.json.get(name)


class WebServer:

    web_filters = []

    app = Flask(__name__)

    @staticmethod
    @app.route('/health', methods=['GET'])
    def health():
        return {'status': 'OK', 'timestamp': f'{datetime.now()}'}

    @staticmethod
    @app.route('/favicon.ico', methods=['GET'])
    def favicon():
        return ''

    @staticmethod
    @app.route('/<path>', methods=['GET', 'POST'])
    def dynamic_get(path: str):
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
    def start():
        serve(app=WebServer.app, host='0.0.0.0', port=8888, threads=BACKBONE_WAITRESS_THREADS)


class Log:

    _stopwatches = {}
    _warning_msgs_count = 0
    _error_msgs_count = 0
    _critical_msgs_count = 0

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
