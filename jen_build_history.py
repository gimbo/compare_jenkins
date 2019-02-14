import argparse
import http.client as httplib
import os
import sys
from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

import requests
from click import echo
from tabulate import tabulate


BASE_ENV_VAR_NAME = 'JEN_COMPARE_DEFAULT_BASE'
DEFAULT_TIMEOUT = 5  # Seconds


BuildInfo = Tuple[
    Optional[int],  # Number
    Optional[bool],  # Building
    Optional[datetime],  # Timestamp
    Optional[int],  # Duration
    Optional[str],  # Revision
    Optional[str],  # Branch name
]


def main():
    args = parse_args()
    try:
        get_and_report_build_history(args.base, args.project, args.timeout)
    except KeyboardInterrupt:
        print()


def get_and_report_build_history(
    base: str,
    project: str,
    timeout: int,
):
    build_history = get_build_history(base, project, timeout)
    if not build_history:
        return
    report_build_history(build_history)


def get_build_history(base: str, project: str, timeout: int) -> List[BuildInfo]:
    api_url = get_project_api_url(base, project)
    result = get_url(api_url, timeout)
    if not result:
        return []
    builds = [parse_build(build) for build in result['builds']]
    return builds


def get_project_api_url(base: str, project: str) -> str:
    tree = (
        'builds[number,building,timestamp,duration,estimatedDuration,'
        'actions[lastBuiltRevision[SHA1,branch[name]]]]'
    )
    url = '{}/job/{}/api/json?depth=1&pretty=true&tree={}'.format(
        base,
        project,
        tree,
    )
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
    return number, building, timestamp, duration, revision, branch_name


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
            [prep_for_tabulation(build) for build in build_history],
            headers=headers,
            tablefmt='plain',
            colalign=('right', 'left', 'right'),
        )
    )


def prep_for_tabulation(build: BuildInfo) -> Tuple[Optional[str], ...]:
    number, building, timestamp, duration, revision, branch_name = build
    number_str = str(number) if number is not None else ''
    duration_str = format_duration(duration) if duration is not None else None
    if building:
        number_str = '* ' + number_str
        duration_str = '?' + duration_str
    return (
        number_str,
        format_timestamp(timestamp) if timestamp is not None else None,
        duration_str,
        revision[:8] if revision else revision,
        branch_name,
    )


def format_timestamp(timestamp):
    return timestamp.strftime('%Y-%m-%d %H:%M:%S')


def format_duration(raw_duration):
    seconds = raw_duration // 1000
    mins, secs = divmod(seconds, 60)
    duration = '{}m{:02}s'.format(mins, secs)
    return duration


def get_url(url: str, timeout: int) -> Any:
    try:
        response = requests.get(url, timeout=timeout)
    except requests.exceptions.ConnectTimeout:
        echo('Timed out: {}'.format(url))
        return {}
    code = response.status_code
    if code != 200:
        echo('{} {}: {}'.format(code, httplib.responses[code], url))
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
        'base', metavar='BASE_URL',
        nargs='?',
        help=(
            'Jenkins URL base (e.g. http://localhost:8000). '
            'If not specified, the default value is taken from the env var '
            '{base_env_var_name} if it is set '
            '(current value: {base_env_var_value}).'
        ).format(
            base_env_var_name=BASE_ENV_VAR_NAME,
            base_env_var_value=default_base or 'none set'
        ),
    )
    parser.add_argument(
        'project', metavar='PROJECT',
        help='Project name (e.g. main)',
    )
    parser.add_argument(
        '-t', '--timeout', metavar='N',
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
