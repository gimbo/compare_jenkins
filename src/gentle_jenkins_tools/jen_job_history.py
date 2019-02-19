import argparse
import http.client as httplib
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, urlunparse

import requests
from click import echo
from tabulate import tabulate


BASE_ENV_VAR_NAME = 'JEN_COMPARE_DEFAULT_BASE'
DEFAULT_TIMEOUT = 5  # Seconds


@dataclass
class BuildInfo:

    number: Optional[int]
    building: Optional[bool]
    timestamp: Optional[datetime]
    duration: Optional[int]
    revision: Optional[str]
    branch_name: Optional[str]

    @property
    def number_str(self) -> Optional[str]:
        if self.number is None:
            return None
        number_str = str(self.number)
        if self.building:
            number_str = '* ' + number_str
        return number_str

    @property
    def duration_str(self) -> Optional[str]:
        if self.duration is None:
            return None
        seconds = self.duration // 1000
        mins, secs = divmod(seconds, 60)
        duration_str: str = '{}m{:02}s'.format(mins, secs)
        if self.building:
            duration_str = '?' + duration_str
        return duration_str

    @property
    def timestamp_str(self) -> Optional[str]:
        if self.timestamp is None:
            return None
        timestamp_str = self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        return timestamp_str

    @property
    def tabulation_line(self) -> Tuple[Optional[str], ...]:
        return (
            self.number_str,
            self.timestamp_str,
            self.duration_str,
            self.revision[:8] if self.revision else None,
            self.branch_name,
        )


def main():
    args = parse_args()
    try:
        get_and_report_build_history(args.base, args.job, args.timeout)
    except KeyboardInterrupt:
        print()


def get_and_report_build_history(base: str, job: str, timeout: int):
    build_history = get_build_history(base, job, timeout)
    if not build_history:
        return
    report_build_history(build_history)


def get_build_history(base: str, job: str, timeout: int) -> List[BuildInfo]:
    api_url = get_job_api_url(base, job)
    result = get_url(api_url, timeout)
    if not result:
        return []
    builds = [parse_build(build) for build in result['builds']]
    return builds


def get_job_api_url(base: str, job: str) -> str:
    tree = (
        'builds[number,building,timestamp,duration,estimatedDuration,'
        'actions[lastBuiltRevision[SHA1,branch[name]]]]'
    )
    url = '{}/job/{}/api/json?depth=1&pretty=true&tree={}'.format(base, job, tree)
    return url


def parse_build(build: Dict[str, Any]) -> BuildInfo:
    number: Optional[int] = build.get('number')
    building: Optional[bool] = build.get('building')
    timestamp: Optional[datetime]
    try:
        raw_timestamp: int = build['timestamp']
    except KeyError:
        timestamp = None
    else:
        timestamp = parse_build_timestamp(raw_timestamp)
    duration: Optional[int]
    duration = build.get('duration')
    if building and duration == 0:
        duration = build.get('estimatedDuration')
    revision, branch_name = get_revision_and_branch_name(build)
    return BuildInfo(number, building, timestamp, duration, revision, branch_name)


def parse_build_timestamp(raw_timestamp: int) -> datetime:
    timestamp = datetime.utcfromtimestamp(raw_timestamp / 1000)
    return timestamp


def get_revision_and_branch_name(
    build: Dict[str, Any]
) -> Tuple[Optional[str], Optional[str]]:
    trigger_data = get_build_trigger_data(build)
    revision = trigger_data.get('SHA1')
    try:
        branch_name = trigger_data['branch'][0]['name']
    except (IndexError, KeyError):
        branch_name = None
    else:
        branch_name = normalise_branch_name(branch_name)
    return revision, branch_name


def get_build_trigger_data(build):
    for action in build.get('actions'):
        if action.get('_class') == 'hudson.plugins.git.util.BuildData':
            return action.get('lastBuiltRevision', {})
    return {}


def normalise_branch_name(branch_name):
    branch_name = branch_name.replace('refs/', '')
    branch_name = branch_name.replace('remotes/', '')
    branch_name = branch_name.replace('origin/', '')
    if branch_name == 'detached':
        return '** detached **'
    return branch_name


def report_build_history(build_history: List[BuildInfo]):
    headers = ('Build', 'Timestamp', 'Time', 'Revision', 'Branch')
    print(
        # Ignoring spurious mypy error on the next line
        tabulate(  # type:ignore
            [build.tabulation_line for build in build_history],
            headers=headers,
            tablefmt='plain',
            colalign=('right', 'left', 'right'),
        )
    )


def get_url(url: str, timeout: int) -> Any:
    try:
        response = requests.get(url, timeout=timeout)
    except requests.exceptions.ConnectTimeout:
        echo('Timed out: {}'.format(url))
        return {}
    code = response.status_code
    if code != 200:
        url_without_query = urlunparse(urlparse(url)[:4] + (None, None))  # type: ignore
        echo('{} {}: {}'.format(code, httplib.responses[code], url_without_query))
        return {}
    return response.json()


def parse_args():
    parser = argparse.ArgumentParser()

    def check_positive(value):
        try:
            ivalue = int(value)
        except ValueError:
            ivalue = 0
        if ivalue <= 0:
            raise argparse.ArgumentTypeError(
                "{} is not a positive integer".format(value)
            )
        return ivalue

    default_base = os.environ.get(BASE_ENV_VAR_NAME)
    parser.add_argument(
        'base',
        metavar='BASE_URL',
        nargs='?',
        help=(
            'Jenkins URL base (e.g. http://localhost:8000). '
            'If not specified, the default value is taken from the env var '
            '{base_env_var_name} if it is set '
            '(current value: {base_env_var_value}).'
        ).format(
            base_env_var_name=BASE_ENV_VAR_NAME,
            base_env_var_value=default_base or 'none set',
        ),
    )
    parser.add_argument('job', metavar='JOB', help='job name (e.g. main)')
    parser.add_argument(
        '-t',
        '--timeout',
        metavar='N',
        type=check_positive,
        help='HTTP timeout in seconds (default: {})'.format(DEFAULT_TIMEOUT),
    )

    args = parser.parse_args()

    if not args.base:
        if default_base:
            args.base = default_base
        else:
            echo(
                'No URL base specified (either on command line or env var); '
                'giving up.'
            )
            sys.exit(1)

    if args.timeout is None:
        args.timeout = DEFAULT_TIMEOUT

    return args


if __name__ == "__main__":
    main()
