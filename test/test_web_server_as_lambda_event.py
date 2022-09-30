import unittest
from quickbelog import Log
from quickbe import endpoint
from quickbeserverless import aws_lambda_handler, HttpSession

GREETING = 'Hello'


@endpoint(validation={
    'name': {'required': True, 'type': 'string'}
}
)
def hello(session: HttpSession):
    return f"{GREETING} {session.get('name')}"


class AsLambdaEventTestCase(unittest.TestCase):

    def test_event(self):
        name = 'Suzi'
        expected_result = f'"{GREETING} {name}"'
        test_event = {
            'path': 'hello',
            'body': {
                'name': name
            }
        }
        result = aws_lambda_handler(event=test_event)
        Log.debug(f'Got result: {result}')
        self.assertIsNotNone(result)
        self.assertEqual(expected_result, result.get('body'))


if __name__ == '__main__':
    unittest.main()
