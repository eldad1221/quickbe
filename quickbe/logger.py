import os
import json
import uuid
import inspect
import logging.handlers
from datetime import datetime

PROCESS_LOG_ID = f'{uuid.uuid4()}'

_root = logging.getLogger()

_root.setLevel(0)

default_log_file_name = f"{datetime.now().replace(microsecond=0)}_{PROCESS_LOG_ID}".replace(' ', '_').replace(':', '-')
FORMAT = '%(asctime)s > %(levelname)s\t%(message)s'
formatter = logging.Formatter(FORMAT)

QUICKBE_LOG_TO_STDOUT = os.getenv('QUICKBE_LOG_TO_STDOUT', 'True')
if QUICKBE_LOG_TO_STDOUT.upper() in ['TRUE', '1', 'YES']:
    stdout_handler = logging.StreamHandler()
    stdout_handler.setFormatter(formatter)
    _root.addHandler(stdout_handler)

LOG_MESSAGE_FORMAT = '{0}({1}) method: {2} \t {3}'


def run_level_source_file(run_level: int = 2) -> str:
    """
    Get the source file name of the calling method.
    :param run_level: Each method in the stack is adding one run level.
    :return: The name of the file that contains the method that called the LogHandler.
    """
    filename = inspect.stack()[run_level][1]
    first, *middle, last = '/prefix{0}'.format(filename).replace('\\', '/').split('/')
    return last


def run_level_source_line_number(run_level: int = 2) -> str:
    """
    Get the line number in the source file name of the calling method.
    :param run_level: Each method in the stack is adding one run level.
    :return: Line number that called the LogHandler.
    """
    return inspect.stack()[run_level][2]


def run_level_method_name(run_level: int = 2) -> str:
    """
    Get the calling method name.
    :param run_level: Each method in the stack is adding one run level.
    :return: Method name that called the LogHandler
    """
    return inspect.stack()[run_level][3]


def _object_dump(obj: object) -> str:
    return json.dumps(obj, default=lambda o: o.__dict__, indent=4)


def log_exception(message: str):
    msg = LOG_MESSAGE_FORMAT.format(
        run_level_source_file(run_level=3),
        run_level_source_line_number(run_level=3),
        run_level_method_name(run_level=3), message
    )
    logging.exception(msg=msg)


def log_msg(level: int, message: object, current_run_level: int = 2) -> None:
    """
    Write a log message.
    :param current_run_level:
    :param level: Logging level 0=NOTSET, 10=DEBUG, 20=INFO, 30=WARNING, 40=ERROR, 50=CRITICAL
    :param message: Object or string
    :return: None
    """
    if not isinstance(message, str):
        message = _object_dump(message)

    logging.log(
        level,
        LOG_MESSAGE_FORMAT.format(
            run_level_source_file(run_level=current_run_level),
            run_level_source_line_number(run_level=current_run_level),
            run_level_method_name(run_level=current_run_level), message
        )
    )


def set_log_level(level: int):
    _root.setLevel(level=level)


def get_log_level() -> int:
    return _root.level


def get_log_level_name() -> str:
    return logging.getLevelName(get_log_level())
