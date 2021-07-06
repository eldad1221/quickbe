import time
import unittest
import backbone
import backbone.logger as lg


class LoggerTestCase(unittest.TestCase):

    def test_basic_log_message(self):
        lg.log_msg(level=20, message='Test message')
        self.assertEqual(True, True)

    def test_debug_message(self):
        backbone.Log.debug(msg='This is a debug message')
        self.assertEqual(True, True)

    def test_info_message(self):
        backbone.Log.info(msg='This is an info message')
        self.assertEqual(True, True)

    def test_warning_message(self):
        backbone.Log.warning(msg='This is a warning message')
        self.assertEqual(True, True)

    def test_error_message(self):
        backbone.Log.error(msg='This is an error message')
        self.assertEqual(True, True)

    def test_critical_message(self):
        backbone.Log.critical(msg='This is a critical message')
        self.assertEqual(True, True)

    def test_stopwatch(self):
        sw_id = backbone.Log.start_stopwatch('Unittest for stopwatch', print_it=True)
        self.assertIsInstance(sw_id, str)

        time.sleep(0.5)
        seconds = backbone.Log.stopwatch_seconds(stopwatch_id=sw_id)
        self.assertGreater(seconds, 0.5)

        time.sleep(0.2)
        seconds = backbone.Log.stopwatch_seconds(stopwatch_id=sw_id)
        self.assertGreater(seconds, 0.7)

        time.sleep(0.1)
        self.assertEqual(True, backbone.Log.stop_stopwatch(stopwatch_id=sw_id, print_it=True))
        self.assertEqual(False, backbone.Log.stop_stopwatch(stopwatch_id=sw_id, print_it=True))


if __name__ == '__main__':
    unittest.main()
