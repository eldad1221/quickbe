from backbone import WebServer, endpoint, Log


@endpoint(path='hi')
def say_hello(req: dict):
    return 'Hello'


@endpoint()
def echo(req: dict):
    return req.get('text')


class World:

    @staticmethod
    @endpoint()
    def hello(req):
        return 'Hello world'


if __name__ == '__main__':
    WebServer.start(apis=[])
