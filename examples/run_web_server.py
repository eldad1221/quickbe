from flask import redirect
from quickbe import WebServer, endpoint, Log, HttpSession


def persona_non_grata(session: HttpSession):
    name = session.get('name', '').lower()
    if name in ['dracula', 'sauron', 'dart', 'molech']:
        session.set_status(401)
        return 'You are not welcome here!'


@endpoint(path='v1/hi', doc='Say hello', example='Hello to you, from V1')
def say_hello_v1(session: HttpSession):
    return f'{say_hello(session=session)}, from V1'


@endpoint(path='hi', doc='Say hello', example='Hello to you')
def say_hello(session: HttpSession):
    name = session.get('name')
    if name is None:
        name = ''
    return f'Hello to you {name}'


@endpoint(validation={
    'text': {
        'required': True, 'type': 'string',
        'doc': 'Some text to echo', 'example': 'Hello world'
    },
    'name': {
        'required': False, 'type': 'string',
        'doc': 'Name, just for testing', 'example': 'John Doe'
    },
    'age': {
        'required': False, 'type': 'integer',
        'doc': 'Persons age', 'example': 42
    },
    'object_info': {
        'doc': 'Object attributes',
        'type': 'dict',
        'allow_unknown': False,
        'required': True,
        'schema': {
            'name': {'type': 'string', 'required': True},
            'description': {'type': 'string', 'required': True},
            'count': {'type': 'integer', 'default': -1, 'example': 42},
            'type': {'type': 'string', 'default': 'abc'}
        }
    }
},
    doc='Echo text'
)
def echo(session: HttpSession):
    return session.get('text')


@endpoint(path='go', validation={
    'to': {
        'type': 'string',
        'required': True,
        'doc': 'Url to redirect to',
        'example': 'https://www.google.com'
    }
})
def goto(session: HttpSession):
    url = session.get('to')
    Log.debug(f'Redirecting to {url}...')
    return redirect(url, code=302)


if __name__ == '__main__':
    WebServer.add_filter(persona_non_grata)
    WebServer.start(port=8888)
