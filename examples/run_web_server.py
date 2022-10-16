from flask import redirect
from quickbe import WebServer, endpoint, Log, HttpSession


def persona_non_grata(session: HttpSession):
    name = session.get('name', '').lower()
    if name in ['dracula', 'sauron', 'dart', 'molech']:
        session.set_status(401)
        return 'You are not welcome here!'


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
    return session.get('text')


@endpoint(path='go', validation={'to': {'type': 'string', 'required': True}})
def goto(session: HttpSession):
    url = session.get('to')
    Log.debug(f'Redirecting to {url}...')
    return redirect(url, code=302)


if __name__ == '__main__':
    WebServer.add_filter(persona_non_grata)
    WebServer.start(port=8888)
