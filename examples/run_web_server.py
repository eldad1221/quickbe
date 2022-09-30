from flask import redirect
from quickbe import WebServer, endpoint, Log
from quickbeserverless import HttpSession


@endpoint(path='hi')
def say_hello(session: HttpSession):
    name = session.get('name')
    if name is None:
        name = ''
    return f'Hello to you {name}'


@endpoint(validation={
    'text': {'required': True, 'type': 'string'},
    'name': {'required': False, 'type': 'string'},
    'age': {'required': False, 'type': 'integer'}
}
)
def echo(session: HttpSession):
    return session.get_parameter('text')


@endpoint(path='go', validation={'to': {'type': 'string', 'required': True}})
def goto(session: HttpSession):
    url = session.get_parameter('to')
    Log.debug(f'Redirecting to {url}...')
    return redirect(url, code=302)


if __name__ == '__main__':
    WebServer.start(port=8888)
