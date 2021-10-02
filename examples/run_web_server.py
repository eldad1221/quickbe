from quickbe import WebServer, HttpSession, endpoint, Log


@endpoint(path='hi')
def say_hello(session: HttpSession):
    return 'Hello'


@endpoint(validation={
    'text': {'required': True, 'type': 'string'},
    'name': {'required': False, 'type': 'string'},
    'age': {'required': False, 'type': 'integer'}
}
)
def echo(session: HttpSession):
    return session.get_parameter('text')


if __name__ == '__main__':
    Log.info(f'Starting web server')
    WebServer.start()
