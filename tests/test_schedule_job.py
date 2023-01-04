import time
import schedule
import unittest
from quickbelog import Log
from quickbe.utils import get_schedule_job, ScheduledJobs

JOB_DEF = [
    'every 3 seconds',
    'every 1 minutes',
    'every minute at :01'
    'every minute at 01:'
    'every day at 12:11',
    'every 6 hours'
]
counter = 0


def do_something(arg: str):
    Log.info(f'Doing something {arg}...')


def just_count(o: object):
    global counter
    counter += 1
    Log.info(f'{counter} Mississippi . . .')


class ScheduleJobTestCase(unittest.TestCase):

    def test_scd_job(self):
        scd_job = get_schedule_job(scd_str='every 1 seconds')
        scd_job.do(just_count, '')
        t = ScheduledJobs()
        t.start()
        Log.debug(f'Jobs: {schedule.jobs}')
        time.sleep(4)
        t.terminate()
        Log.debug(f'Jobs: {schedule.jobs}')

        self.assertGreater(counter, 2)

    def test_job_def(self):
        for s in JOB_DEF:
            Log.debug(f'Try to parse definition: {s}')
            scd_job = get_schedule_job(scd_str=s)
            scd_job.do(do_something, s)
        Log.debug(f'Jobs: {schedule.jobs}')
        self.assertEqual(True, True)


if __name__ == '__main__':
    unittest.main()
