import json
import uuid
from git import Repo
from glob import iglob
from pathlib import Path
from os.path import join
from os import listdir, getenv
from cryptography.fernet import Fernet

QUICKBE_VAULT_HOME_FOLDER = getenv('QUICKBE_VAULT_HOME_FOLDER', f'{Path.home()}/vault')
QUICKBE_VAULT_KEYS_FOLDER = getenv('QUICKBE_VAULT_KEYS_FOLDER', f'{QUICKBE_VAULT_HOME_FOLDER}/keys')
QUICKBE_VAULT_REPOSITORIES_FOLDER = getenv('QUICKBE_VAULT_REPOSITORIES_FOLDER', f'{QUICKBE_VAULT_HOME_FOLDER}/repos')
KEY_TOKEN_STR = '~token~'
CURRENT_KEY_STR = 'current_key'
VAULT_KEY_PATH = f'{QUICKBE_VAULT_KEYS_FOLDER}/{KEY_TOKEN_STR}.key'
SECRET_FILE_SUFFIX = '.scr'


QUICKBE_VAULT_ALL_KEYS = {}


def generate_crypto_key(add_salt: bool = False) -> (bytes, str):
    """
    Generates crypto key and store it into a file
    :param add_salt: Salted key
    :return: Tuple of key bytes and key token as string
    """
    crypto_key = Fernet.generate_key()
    key_folder = Path(QUICKBE_VAULT_KEYS_FOLDER)
    if not key_folder.is_dir():
        key_folder.mkdir(parents=True)
    key_token = str(uuid.uuid4())
    file_path = VAULT_KEY_PATH.replace(KEY_TOKEN_STR, key_token)
    file = open(file_path, 'wb')
    file.write(crypto_key)
    file.close()

    file_path = VAULT_KEY_PATH.replace(KEY_TOKEN_STR, CURRENT_KEY_STR)
    file = open(file_path, 'w')
    file.write(key_token)
    file.close()

    global QUICKBE_VAULT_ALL_KEYS
    QUICKBE_VAULT_ALL_KEYS[key_token] = crypto_key
    QUICKBE_VAULT_ALL_KEYS[CURRENT_KEY_STR] = key_token
    return crypto_key, key_token


def read_key(key_token: str, full_path: bool = False) -> str:
    """
    Reads key by token or full path
    :param key_token: Key token
    :param full_path: If true, key_token must contain full path to key file
    :return: Key bytes
    """
    if full_path:
        file_path = key_token
    else:
        file_path = VAULT_KEY_PATH.replace(KEY_TOKEN_STR, key_token)
    file = open(file_path, 'r')
    key = file.read()
    file.close()
    return key


def encrypt(key_token: str, data: str) -> str:
    key = read_key(key_token=key_token)
    my_crypt = Fernet(key.encode())
    encrypted_data = my_crypt.encrypt(data.encode()).decode()
    return encrypted_data


def decrypt(key_token: str, data: str) -> str:
    if isinstance(data, str):
        data = data.encode()
    key = read_key(key_token=key_token)
    my_crypt = Fernet(key.encode())
    decrypted_data = my_crypt.decrypt(data).decode()
    return decrypted_data


def load_all_keys() -> dict:
    all_keys = {}
    key_files = [f for f in listdir(QUICKBE_VAULT_KEYS_FOLDER) if Path(join(QUICKBE_VAULT_KEYS_FOLDER, f)).is_file()]
    for file in key_files:
        key_token = str(file).replace('.key', '')
        key = read_key(key_token=key_token)
        all_keys[key_token] = key

    global QUICKBE_VAULT_ALL_KEYS
    QUICKBE_VAULT_ALL_KEYS = all_keys
    return all_keys


DEFAULT_VAULT = 'default_vault'


def get_repo(name: str = DEFAULT_VAULT) -> Repo:
    repo_path = f'{QUICKBE_VAULT_REPOSITORIES_FOLDER}/{name}'
    if not Path(repo_path).is_dir():
        Repo.init(path=repo_path)

    repo = Repo(path=repo_path)
    return repo


def get_repo_path(repo) -> str:
    return repo.git.working_dir


def save_secret(secret_path: str, secret_name: str, value: str, comment: str):
    secret_name = secret_name.upper()
    secret_path = secret_path.lower()
    repo = get_repo()
    path = Path(join(get_repo_path(repo=repo), secret_path))
    if not path.is_dir():
        path.mkdir(parents=True)

    file = open(join(path, f'{secret_name}{SECRET_FILE_SUFFIX}'), 'w')
    current_token = QUICKBE_VAULT_ALL_KEYS[CURRENT_KEY_STR]
    data = {
        'token': current_token,
        'value': encrypt(key_token=current_token, data=value),
        'comment': comment
    }
    file.write(json.dumps(data))
    file.close()


def read_secret(secret_name: str, secret_path: str) -> str:
    return read_secret_data(secret_name=secret_name, secret_path=secret_path).get('value')


def read_secret_data(secret_name: str, secret_path: str) -> dict:
    repo = get_repo()
    path = Path(join(get_repo_path(repo=repo), secret_path))
    if not path.is_dir():
        raise FileNotFoundError(f'Cant find secret path {secret_path}.')

    file = open(join(path, f'{secret_name}.scr'), 'r')
    current_token = QUICKBE_VAULT_ALL_KEYS[CURRENT_KEY_STR]
    data = json.load(file)
    file.close()
    comment = data.get('comment')
    value = decrypt(key_token=data['token'], data=data['value'])
    return {'value': value, 'comment': comment}


def _remove_prefix(s: str, prefix: str) -> str:
    if s.startswith(prefix):
        return s.replace(prefix, '', 1)
    else:
        return s


def _remove_suffix(s: str, suffix: str) -> str:
    if s.endswith(suffix):
        return s[:(len(suffix)*-1)]
    else:
        return s


def list_secret(secret_path: str) -> list:
    secret_path = secret_path.lower()
    repo = get_repo()
    path = Path(join(get_repo_path(repo=repo), secret_path))
    if path.is_dir():
        children = [
            _remove_prefix(str(file), str(path)).replace('\\', '/') for file in iglob(f'{path}/**/*', recursive=True)
        ]
        return [_remove_prefix(child, '/') for child in children]
    else:
        raise FileNotFoundError(f'Cant find secrets path {secret_path}.')


def get_secrets(secret_path: str) -> dict:

    secrets = [_remove_suffix(s=secret, suffix=SECRET_FILE_SUFFIX) for secret in list_secret(secret_path=secret_path) if str(secret).endswith(SECRET_FILE_SUFFIX)]
    data = {}
    for secret in secrets:
        data[secret] = read_secret(secret_path=secret_path, secret_name=secret)
    return data


AUTHORIZATION_FILE_NAME = '.auth'
AUTHORIZATION_FILE_USERS_KEY = 'users'
AUTHORIZATION_FILE_GROUPS_KEY = 'groups'


def is_authorized_to_path(user: str, secret_path: str) -> bool:
    folders = secret_path.split('/')
    path = get_repo_path(repo=get_repo())
    for folder in folders:
        path = f'{path}/{folder}'
        try:
            f = open(f'{path}/{AUTHORIZATION_FILE_NAME}')
            auth = json.load(f)
            if AUTHORIZATION_FILE_USERS_KEY in auth and user in auth.get(AUTHORIZATION_FILE_USERS_KEY):
                return True
        except FileNotFoundError:
            pass
    return False
