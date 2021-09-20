import inspect
from backbone import Log
from abc import abstractmethod


def endpoint(path: str):

    def decorator(func):
        Log.debug(f'Path: {path} form method {func}')
        return func

    return decorator


# @endpoint(path='my_path')
# def my_endpoint():
#     Log.debug('Hello')


class Endpoint:

    @endpoint(path='my_endpoint_path')
    def do(self) -> int:
        Log.debug('Doing...')

    @endpoint(path='my_endpoint_path')
    def do2(self) -> int:
        Log.debug('Doing...')


if __name__ == '__main__':
    # Endpoint().do()
    Endpoint().do()
    # Log.info(f'{inspect.getsource(Endpoint)}')
    Log.info(f'{dir(Endpoint())}')

