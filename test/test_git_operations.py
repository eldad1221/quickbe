import unittest
from backbone import Log
import backbone.vault as vault


class GitTestCase(unittest.TestCase):

    def test_clone(self):
        repo = vault.get_repo()
        Log.debug(str(repo))
        self.assertEqual(True, True)


if __name__ == '__main__':
    unittest.main()
