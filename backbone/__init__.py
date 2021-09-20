import uuid
from flask import Flask, request
import backbone.logger as b_logger
from datetime import datetime, timedelta

WEB_SERVER_ENDPOINTS = {}


def endpoint(path: str = None):

    def decorator(func):
        global WEB_SERVER_ENDPOINTS
        if path is None:
            web_path = str(func.__qualname__).lower().replace('.', '/')
        else:
            web_path = path
        Log.debug(f'Registering endpoint: Path={web_path}, Function={func}')
        WEB_SERVER_ENDPOINTS[web_path] = func
        return func

    return decorator


class WebServer:

    app = Flask(__name__)

    @staticmethod
    @app.route('/health', methods=['GET'])
    def health():
        return 'OK'

    @staticmethod
    @app.route('/<path>', methods=['GET'])
    def dynamic_get(path: str):
        req_body = dict(request.args)
        return WEB_SERVER_ENDPOINTS.get(path)(req_body)

    @staticmethod
    @app.route('/<path>', methods=['POST'])
    def dynamic_post(path: str):
        req_body = dict(request.get_json())
        return WEB_SERVER_ENDPOINTS.get(path)(req_body)

    @staticmethod
    def start(apis: list):
        WebServer.app.run(host='0.0.0.0', port=8888)


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
