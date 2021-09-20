import uuid
from pathlib import Path
from os.path import join
from os import listdir, getenv
from cryptography.fernet import Fernet

BACKBONE_VAULT_KEYS_FOLDER = getenv('BACKBONE_VAULT_KEYS_FOLDER', f'{Path.home()}/vault/keys')
KEY_TOKEN_STR = '~token~'
VAULT_KEY_PATH = f'{BACKBONE_VAULT_KEYS_FOLDER}/{KEY_TOKEN_STR}.key'


def generate_crypto_key(add_salt: bool = False) -> (bytes, str):
    """
    Generates crypto key and store it into a file
    :param add_salt: Salted key
    :return: Tuple of key bytes and key token as string
    """
    crypto_key = Fernet.generate_key()
    key_folder = Path(BACKBONE_VAULT_KEYS_FOLDER)
    if not key_folder.is_dir():
        key_folder.mkdir(parents=True)
    key_token = str(uuid.uuid4())
    file_path = VAULT_KEY_PATH.replace(KEY_TOKEN_STR, key_token)
    file = open(file_path, 'wb')
    file.write(crypto_key)
    file.close()
    return crypto_key, key_token


def read_key(key_token: str, full_path: bool = False) -> bytes:
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
    file = open(file_path, 'rb')
    key = file.read()
    file.close()
    return key


def encrypt(key_token: str, data: str) -> str:
    key = read_key(key_token=key_token)
    my_crypt = Fernet(key)
    encrypted_data = my_crypt.encrypt(data.encode()).decode()
    return encrypted_data


def decrypt(key_token: str, data: str) -> str:
    if isinstance(data, str):
        data = data.encode()
    key = read_key(key_token=key_token)
    my_crypt = Fernet(key)
    decrypted_data = my_crypt.decrypt(data).decode()
    return decrypted_data


def load_all_keys() -> dict:
    all_keys = {}
    key_files = [f for f in listdir(BACKBONE_VAULT_KEYS_FOLDER) if Path(join(BACKBONE_VAULT_KEYS_FOLDER, f)).is_file()]
    for file in key_files:
        key_token = str(file).replace('.key', '')
        key = read_key(key_token=key_token)
        all_keys[key_token] = key
    return all_keys


