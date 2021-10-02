import json
import quickbe.vault as vault
from quickbe import WebServer, endpoint, Log, get_env_var, HttpSession

SECRET_NAME_KEY = 'secret_name'
SECRET_PATH_KEY = 'secret_path'
SECRET_VALUE_KEY = 'value'


VAULT_SERVER_USERS = {}


QUICKBE_VAULT_SERVER_APIKEY_HEADER = get_env_var('QUICKBE_VAULT_SERVER_APIKEY_HEADER', 'x-api-key')
QUICKBE_VAULT_SERVER_USER_HEADER = 'x-quickbe-vault-user'


def check_api_key(session: HttpSession) -> int:
    if QUICKBE_VAULT_SERVER_APIKEY_HEADER in session.request.headers:
        apikey = session.request.headers.get(QUICKBE_VAULT_SERVER_APIKEY_HEADER)
        user_name = VAULT_SERVER_USERS.get(apikey)
        if user_name is not None:
            session.response.headers[QUICKBE_VAULT_SERVER_USER_HEADER] = user_name
            return 200
    session.response.response = 'Unauthorized'
    return 401


def _get_user(session: HttpSession) -> str:
    return session.response.headers[QUICKBE_VAULT_SERVER_USER_HEADER]


def _is_authorized_to_path(session: HttpSession, secret_path: str) -> bool:
    if not secret_path.startswith('/'):
        secret_path = f'/{secret_path}'
    is_authorized = vault.is_authorized_to_path(user=_get_user(session=session), secret_path=secret_path)
    if not is_authorized:
        session.response.status = 403
        session.response.response = 'No permission'
    return is_authorized


def load_users():
    repo_path = vault.get_repo_path(vault.get_repo())
    f = open(file=f'{repo_path}/.users', mode='r')
    users = json.load(f)
    users_directory = {}
    for user, user_data in users.items():
        key_token, encrypted_data = user_data.split('.')
        users_directory[vault.decrypt(key_token=key_token, data=encrypted_data)] = user
    global VAULT_SERVER_USERS
    VAULT_SERVER_USERS = users_directory


@endpoint(path='get', validation={
    SECRET_NAME_KEY: {'required': True, 'type': 'string'},
    SECRET_PATH_KEY: {'required': True, 'type': 'string'},
}
          )
def read_secret(session: HttpSession):
    secret_path = session.get_parameter(SECRET_PATH_KEY)
    if _is_authorized_to_path(session=session, secret_path=secret_path):
        if not _is_authorized_to_path(session=session, secret_path=secret_path):
            session.response.status = 403
        return vault.read_secret(
            secret_name=session.get_parameter(SECRET_NAME_KEY),
            secret_path=secret_path
        )


@endpoint(path='put', validation={
    SECRET_NAME_KEY: {'required': True, 'type': 'string'},
    SECRET_PATH_KEY: {'required': True, 'type': 'string'},
    SECRET_VALUE_KEY: {'required': True, 'type': 'string'},
}
          )
def save_secret(session: HttpSession):
    secret_path = session.get_parameter(SECRET_PATH_KEY)
    if _is_authorized_to_path(session=session, secret_path=secret_path):
        try:
            vault.save_secret(
                secret_name=session.get_parameter(SECRET_NAME_KEY),
                secret_path=session.get_parameter(SECRET_PATH_KEY),
                value=session.get_parameter(SECRET_VALUE_KEY)
            )
            return 'DONE'
        except Exception as ex:
            Log.error(f'Error while saving secret: {ex}')
            raise ex


@endpoint(path='list', validation={
    SECRET_PATH_KEY: {'required': True, 'type': 'string'},
}
          )
def list_secrets(session: HttpSession):
    secret_path = session.get_parameter(SECRET_PATH_KEY)
    if _is_authorized_to_path(session=session, secret_path=secret_path):
        return {'secrets': vault.list_secret(secret_path=secret_path)}


@endpoint(validation={
    SECRET_PATH_KEY: {'required': True, 'type': 'string'},
}
          )
def get_secrets(session: HttpSession):
    secret_path = session.get_parameter(SECRET_PATH_KEY)
    if _is_authorized_to_path(session=session, secret_path=secret_path):
        return vault.get_secrets(secret_path=secret_path)


def run_me():
    load_users()
    vault.load_all_keys()
    WebServer.add_filter(check_api_key)
    WebServer.start()


if __name__ == '__main__':
    run_me()
