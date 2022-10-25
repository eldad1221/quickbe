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
            'lat': {'type': 'float', 'required': True},
            'long': {'type': 'float', 'required': True},
            'name': {'type': 'string', 'required': True},
            'description': {'type': 'string', 'required': True},
            'quantity': {'type': 'integer', 'default': -1},
            'lifespan': {'type': 'integer', 'default': -1},
            'attachments_url': {'type': 'list'},
            'color': {'type': 'string', 'default': '#4285F4'},
            'type': {'type': 'string', 'default': 'c0'},
            'qr_code': {'type': 'boolean', 'default': False},
        }
    }
}
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
