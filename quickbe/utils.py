import random
import string
import schedule
from threading import Thread, Event


def generate_token(chars: str = None, length: int = 32) -> str:
    if chars is None:
        chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def get_schedule_job(scd_str: str) -> schedule.Job:
    """
    Parse and return schedule job.
    Extra documentation: https://schedule.readthedocs.io/en/stable/examples.html
    :param scd_str:
    :return:
    """
    schedule_job = schedule
    tokens = scd_str.strip().lower().split(' ')
    if tokens[0] == 'every':
        if tokens[1].isdigit():
            units = tokens[1]
            schedule_job = schedule_job.every(int(units))
            unit_name = tokens[2]
            if unit_name == 'seconds':
                schedule_job = schedule_job.seconds
            elif unit_name == 'minutes':
                schedule_job = schedule_job.minutes
            elif unit_name == 'hours':
                schedule_job = schedule_job.hours
            elif unit_name == 'days':
                schedule_job = schedule_job.days
        else:
            schedule_job = schedule_job.every()
            unit_name = tokens[1]
            if unit_name == 'second':
                schedule_job = schedule_job.second
            elif unit_name == 'minute':
                schedule_job = schedule_job.minute
            elif unit_name == 'hour':
                schedule_job = schedule_job.hour
            elif unit_name == 'day':
                schedule_job = schedule_job.day
            if tokens[2] == 'at' and tokens[3].replace(':', '').isdigit() and ':' in tokens[3]:
                schedule_job = schedule_job.at(tokens[3])
    else:
        raise schedule.ScheduleValueError(f'Scheduler definition must start with `every` {scd_str}')

    if not isinstance(schedule_job, schedule.Job):
        raise schedule.ScheduleValueError(f'Scheduler definition has an error {scd_str}')
    return schedule_job


class ScheduledJobs(Thread):

    def __init__(self, wait_interval: int = 1):
        self.stop_event = Event()
        self.wait_interval = wait_interval
        super(ScheduledJobs, self).__init__()

    def run(self):
        while not self.stop_event.is_set():
            schedule.run_pending()
            self.stop_event.wait(self.wait_interval)

    def terminate(self):
        self.stop_event.set()
