import logging
import pathlib
import re
from datetime import date, datetime
import ast
import itertools

logger = logging.getLogger(__name__)

FS_MAPPING = {
    'FS00': 'CPU',
    'FS01': 'GPU'
}


class ScoreEntry:
    __slots__ = ['start', 'end', 'duration',
                 'project', 'slot', 'unit', 'points']

    def __init__(self, project=None, start=None, end=None, duration=None, slot=None, unit=None, points=None):
        self.project = project
        self.start = start
        self.end = end
        self.duration = duration
        self.slot = slot
        self.unit = unit
        self.points = points

    def calculate_duration(self):
        diff = datetime.fromisoformat(
            self.end)-datetime.fromisoformat(self.start)
        self.duration = str(diff)

    def __str__(self):
        return '\t'.join([self.start, self.end, self.duration, self.project, FS_MAPPING[self.slot], self.unit, str(self.points)])


class ScoreBoard:
    DATE_REGEX = re.compile(
        r'log-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})-\d+')
    LINE_REGEX = re.compile(
        r'(?P<time>\d{2}:\d{2}:\d{2})(:(?P<level>[A-Z]+))?:(?P<unit>WU\d+):(?P<slot>FS\d+)(:(?P<type>(0x|0X)[a-fA-F0-9]+))?:((Project: (?P<project_id>\d+) \(Run (?P<run>\d+), Clone (?P<clone>\d+), Gen (?P<gen>\d+)\))|(Final credit estimate, (?P<points>[\d\.]+) points)|(((?P<msg_type>(ERROR|Exception)): ?)?(?P<msg>[\w ,]+)))')

    def __init__(self):
        self.scores = []
        self.started = []
        self.current_date = None

    def read_log(self, log_file):
        file = pathlib.Path(log_file)
        log = file.read_text()

        self.set_current_date_from_file(file)

        for line in log.splitlines():
            try:
                self.handle_line(line)
            except:
                pass
            continue

    def handle_line(self, line):
            info = self.LINE_REGEX.match(line).groupdict()

            if info['project_id']:
                self._handle_start(info)
            elif info['points']:
                self._handle_end(info)

    def set_current_date_from_file(self, file_name):
        name = pathlib.Path(file_name).stem

        match = self.DATE_REGEX.match(name)

        if not match:
            self.current_date = date.today()
            return

        self.current_date = date(
            year=int(match.group('year')),
            month=int(match.group('month')),
            day=int(match.group('day')),
        )

    def _handle_start(self, info):
        entry = ScoreEntry(
            start=f'{self.current_date}T{info["time"]}',
            project=info['project_id'],
            slot=info['slot'],
            unit=info['unit'],
        )

        same = [e for e in self.started if e.slot ==
                entry.slot and e.project == entry.project and e.unit == entry.unit]

        if not same:
            self.started.append(entry)

    def _handle_end(self, info):
        end = f'{self.current_date}T{info["time"]}'
        slot = info['slot']
        points = ast.literal_eval(info['points'])
        unit = info['unit']

        found = None
        for entry in self.started:
            if slot == entry.slot and unit == entry.unit:
                found = entry

        if not found:
            return

        self.started.remove(found)

        found.end = end
        found.points = points
        found.calculate_duration()

        self.scores.append(found)

    def __str__(self):
        return '\n'.join([str(entry) for entry in self.scores])

    def total_points(self):
        total = 0.

        for entry in self.scores:
            total += entry.points

        return total