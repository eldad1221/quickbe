import os.path
import unittest
from backbone import Log
import backbone.vault as vault


class CryptoTestCase(unittest.TestCase):

    def test_save_crypt_key(self):
        key, key_token = vault.generate_crypto_key()
        file_path = vault.VAULT_KEY_PATH.replace(vault.KEY_TOKEN_STR, key_token)
        Log.debug(f'Key: {key}')
        self.assertEqual(True, os.path.isfile(file_path))

    def test_encrypt_and_decrypt(self):
        original_data = 'Hello world'
        key, key_token = vault.generate_crypto_key()
        encrypted_data = vault.encrypt(key_token=key_token, data=original_data)
        Log.debug(f'Encrypted data: {encrypted_data}')
        decrypted_data = vault.decrypt(key_token=key_token, data=encrypted_data)
        Log.debug(f'Decrypted data: {decrypted_data}')

        self.assertEqual(original_data, decrypted_data)

    def test_read_key(self):
        key, key_token = vault.generate_crypto_key()
        file_path = vault.VAULT_KEY_PATH.replace(vault.KEY_TOKEN_STR, key_token)
        self.assertEqual(True, os.path.isfile(file_path))
        self.assertEqual(key, vault.read_key(key_token=key_token))

    def test_load_all_keys(self):
        key, key_token = vault.generate_crypto_key()
        Log.debug(f'Token: {key_token}, Key: {key}')
        all_keys = vault.load_all_keys()
        Log.debug(f'{all_keys}')
        self.assertEqual(True, key_token in all_keys)


if __name__ == '__main__':
    unittest.main()
