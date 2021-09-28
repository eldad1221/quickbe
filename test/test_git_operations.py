import uuid
import datetime
import unittest
from os.path import join
from backbone import Log
import backbone.vault as vault


class GitTestCase(unittest.TestCase):

    def test_clone(self):
        repo = vault.get_repo()
        Log.debug(vault.get_repo_path(repo=repo))
        self.assertEqual(True, True)

    def test_add_and_commit(self):
        repo = vault.get_repo()
        repo_path = vault.get_repo_path(repo=repo)
        Log.info(repo_path)

        file_name = f'New_file_{uuid.uuid4()}.txt'
        file = open(file=join(repo_path, file_name), mode='w')
        file.write('Delete me.')
        file.close()

        files_to_add = repo.untracked_files
        Log.info(f'Files to add: {files_to_add}')
        repo.index.add(items=files_to_add)
        repo.index.commit(message=f'Unittest {datetime.datetime.now()}')
        self.assertGreater(len(files_to_add), 0)


if __name__ == '__main__':
    unittest.main()
