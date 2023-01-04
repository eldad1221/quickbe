import os
import uuid
import quickbe
import unittest
import quickbe.utils as ut


class UtilsTestCase(unittest.TestCase):

    def test_generate_token(self):
        self.assertEqual(32, len(ut.generate_token()))
        self.assertEqual(64, len(ut.generate_token(length=64)))
        translate_table = ''.maketrans("abc", "***")
        self.assertEqual('**********', ut.generate_token(chars='abc', length=10).translate(translate_table))


if __name__ == '__main__':
    unittest.main()
