from backbone import WebServer, endpoint, Log


@endpoint(path='hi')
def say_hello(req: dict):
    # Log.debug(req.get('text'))
    return 'Hello'


@endpoint(validation={'text': {'required': True, 'type': 'string'}})
def echo(req: dict):
    return req.get('text')


if __name__ == '__main__':
    WebServer.start()
