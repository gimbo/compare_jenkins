import argparse
import os
import sys
from datetime import datetime

import requests
from click import echo


try:
    import http.client as httplib
except ImportError:
    import httplib


BASE_ENV_VAR_NAME = 'JEN_COMPARE_DEFAULT_BASE'
DEFAULT_TIMEOUT = 5  # Seconds


def main():
    args = parse_args()
    try:
        get_and_report_build_history(args.base, args.project, args.timeout)
    except KeyboardInterrupt:
        print()


def get_and_report_build_history(base, project, timeout):
    build_history = get_build_history(base, project, timeout)
    if not build_history:
        return
    report_build('ID', 'Timestamp', 'Time', 'Revision', 'Branch')
    for build_id, build_url in build_history:
        build_info = get_build_info(build_url, timeout)
        report_build(build_id, *build_info)


def get_build_history(base, project, timeout):
    project_api_url = get_project_api_url(base, project)
    result = get_url(project_api_url, timeout)
    if not result:
        return []
    builds = sorted((
        (build['number'], build['url'])
        for build in result['builds']
    ), reverse=True)
    return builds


def get_project_api_url(base, project):
    return get_api_url('{}/{}/'.format(base, project))


def get_api_url(url):
    return '{}api/json'.format(url)


def get_build_info(build_url, timeout):
    build_api_url = get_api_url(build_url)
    result = get_url(build_api_url, timeout)
    if not result:
        return '???', '???', '???', '???'
    timestamp = parse_build_timestamp(result)
    duration = parse_build_duration(result)
    revision, branch_name = get_revision_and_branch_name(result)
    return timestamp, duration, revision, branch_name


def parse_build_timestamp(result):
    try:
        raw_timestamp = result['timestamp']
    except KeyError:
        return '???'
    timestamp = datetime.utcfromtimestamp(raw_timestamp / 1000)
    return timestamp.strftime('%Y-%m-%d %H:%M:%S')


def parse_build_duration(result):
    try:
        raw_duration = result['duration']
    except KeyError:
        return '???'
    seconds = raw_duration // 1000
    mins, secs = divmod(seconds, 60)
    duration = '{}m{:02}s'.format(mins, secs)
    return duration


def get_revision_and_branch_name(result):
    build_data_action = get_build_data_action(result)
    try:
        last_built = build_data_action['lastBuiltRevision']
        branch = last_built['branch'][0]
    except KeyError:
        return '???', '???'
    revision = branch.get('SHA1', '???')
    branch_name = normalise_branch_name(branch.get('name', '???'))
    return revision, branch_name


def get_build_data_action(result):
    for action in result['actions']:
        if 'hudson.plugins.git.util.BuildData' in action.get('_class', ''):
            return action
    return {}


def normalise_branch_name(branch_name):
    branch_name = branch_name.replace('refs/', '')
    branch_name = branch_name.replace('remotes/', '')
    branch_name = branch_name.replace('origin/', '')
    if branch_name == 'detached':
        return '** detached **'
    return branch_name


def report_build(build_id, timestamp, duration, revision, branch_name):
    template = '{:<4}  {:19}  {:>6}  {:<8}  {}'
    print(template.format(
        build_id, timestamp, duration, revision[:8], branch_name
    ))


def get_url(url, timeout):
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
            'Jenkins URL base (e.g. http://localhost:8000/job). '
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
