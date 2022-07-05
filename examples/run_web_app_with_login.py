import os
import pathlib
import datetime
import requests
from cachetools import TTLCache
from dotenv import load_dotenv
from google.oauth2 import id_token
from pip._vendor import cachecontrol
import google.auth.transport.requests
from quickbe.oauth import get_authorization_flow
from google_auth_oauthlib.flow import Flow
from flask import abort, redirect, request
from quickbe import WebServer, HttpSession, endpoint, Log, get_env_var


load_dotenv()

GOOGLE_CLIENT_ID = get_env_var('GOOGLE_CLIENT_ID')
USER_SESSION_TIMEOUT = 900
USER_TOKEN_KEY = 'user-token'

HOME_PAGE_HTML = "<h2>Welcome</h2><a href='/login'><button>Login</button></a>"
HELLO_PAGE_HTML = """
<h2>Hello ~name~</h2>
<p>Time is ~time~</p>
<p><a href='/hello?user-token=~token~'><button>Refresh</button></a></p>
<p><a href='/logout'><button>Logout</button></a></p>
"""

client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

AUTHORIZATION_FLOW = get_authorization_flow()

WebServer.app.secret_key = get_env_var("APP_SECRET_KEY")
Log.info(f'App secret key: {WebServer.app.secret_key}')
users_session_token = TTLCache(maxsize=1000, ttl=USER_SESSION_TIMEOUT)


def get_user_token(h_session: HttpSession) -> str:
    user_token = h_session.get_parameter(name=USER_TOKEN_KEY, default=h_session.response.headers.get(USER_TOKEN_KEY))
    try:
        AUTHORIZATION_FLOW.fetch_token(authorization_response=h_session.request.url)
        if user_token is None:
            user_token = request.args["state"]
    except Exception:
        pass
    return user_token


@WebServer.app.route('/home')
def home():
    return HOME_PAGE_HTML


@WebServer.app.route('/login')
def login():
    authorization_url, state = AUTHORIZATION_FLOW.authorization_url()
    users_session_token[state] = 'OK'
    return redirect(location=authorization_url)


@endpoint(path='logout')
def logout(h_session: HttpSession):
    # TODO Get token key to pop
    users_session_token.pop()
    h_session.set_status(302)
    return redirect("/health")


@endpoint(path='hello')
def say_hello(h_session: HttpSession):
    user_token = h_session.response.headers.get(USER_TOKEN_KEY)
    name = h_session.get_parameter(name='name', default=h_session.response.headers.get("user-name"))
    return HELLO_PAGE_HTML.replace(
        '~name~', name).replace(
        '~time~', str(datetime.datetime.now())).replace(
        '~token~', user_token)


def oauth_filter(h_session: HttpSession):
    global users_session_token
    try:
        user_token = get_user_token(h_session=h_session)
        credentials = AUTHORIZATION_FLOW.credentials
        request_session = requests.session()
        cached_session = cachecontrol.CacheControl(request_session)
        token_request = google.auth.transport.requests.Request(session=cached_session)

        id_info = id_token.verify_oauth2_token(
            id_token=credentials._id_token,
            request=token_request,
            audience=GOOGLE_CLIENT_ID
        )
        if user_token not in users_session_token:
            raise KeyError('State does not match')
        h_session.response.headers['user-name'] = id_info.get("name")
        h_session.response.headers[USER_TOKEN_KEY] = user_token
        h_session.response.headers['user-id'] = id_info.get("sub")
        return 200
    except Exception as ex:
        Log.exception('Token not valid.')
        return redirect(location='/login')


if __name__ == '__main__':
    WebServer.add_filter(oauth_filter)
    WebServer.start()
