import unittest
import backbone as bb


def demo_1(session: bb.HttpSession):
    return session.get_parameter('text')


def demo_2(session: bb.HttpSession, s: str):
    return session.get_parameter('text')


def demo_3(session: str):
    return 'text'


class WebServerTestCase(unittest.TestCase):

    def test_http_handler(self):

        self.assertEqual(True, bb._is_valid_http_handler(func=demo_1))

        with self.assertRaises(TypeError):
            self.assertEqual(True, bb._is_valid_http_handler(func=demo_2))

        with self.assertRaises(TypeError):
            self.assertEqual(True, bb._is_valid_http_handler(func=demo_3))


if __name__ == '__main__':
    unittest.main()
