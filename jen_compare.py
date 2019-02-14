import argparse
import os
import sys
from xml.etree import ElementTree

import click
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
        get_and_report_comparison(args.base, args.left, args.right, args.timeout)
    except KeyboardInterrupt:
        print()


def get_and_report_comparison(base, left, right, timeout):

    echo('Fetching failures from left branch')
    left_fails = get_fails(base, left, timeout)
    echo('Fetching failures from right branch')
    right_fails = get_fails(base, right, timeout)

    fail_only_left = sorted(left_fails - right_fails)
    fail_only_right = sorted(right_fails - left_fails)

    echo("Failed in the left branch..: {}".format(len(left_fails)))
    echo("Failed in the right branch.: {}".format(len(right_fails)))
    echo()

    list_side_failures(fail_only_left, left_fail=True, right_fail=False)
    echo()
    list_side_failures(fail_only_right, left_fail=False, right_fail=True)


def get_fails(base, branch, timeout):
    url = get_fails_api_url(base, branch)
    fails_xml = get_url(url, timeout).decode('utf-8')
    failures = parse_fails_xml(fails_xml)
    return failures


def get_fails_api_url(base, branch):
    xpath = "xpath=//case[status='FAILED' or status='REGRESSION']&wrapper=suite"
    tree = "tree=suites[cases[status,className,name]]"
    url = '{}/job/{}/testReport/api/xml?{}&{}'.format(base, branch, xpath, tree)
    return url


def parse_fails_xml(fails_xml):
    tree = ElementTree.fromstring(fails_xml)
    failures = {
        (element.find('className').text, element.find('name').text)
        for element in tree if element.tag == 'case'
    }
    return failures


def get_url(url, timeout):
    try:
        response = requests.get(url, timeout=timeout)
    except requests.exceptions.ConnectTimeout:
        echo('Timed out: {}'.format(url))
        sys.exit(1)
    code = response.status_code
    if code != 200:
        echo('{} {}: {}'.format(code, httplib.responses[code], url))
        sys.exit(1)
    return response.content


def list_side_failures(failures, left_fail, right_fail):

    pretty = style('===', fg='yellow')
    failed = style('failed', fg='red')
    passed = style('passed', fg='green')

    def side_words(side, failure):
        return '{} {}'.format(side, failed if failure else passed)

    msg = '{pretty} {left_words}, {right_words}: {count} {pretty}'.format(
        pretty=pretty,
        left_words=side_words('left', left_fail),
        right_words=side_words('right', right_fail),
        count=len(failures),
    )
    echo(msg)

    for failure in failures:
        echo(failure_name(*failure))


def failure_name(class_name, test_name):
    return '{}.{}'.format(class_name, test_name)


style = click.style


def style_monochrome(msg, *args, **kwargs):
    return msg


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
        'left', metavar='LEFT',
        help=(
            'Path to left hand target (e.g. main)'
        ),
    )
    parser.add_argument(
        'right', metavar='RIGHT',
        help=(
            'Path to right hand target (e.g. some-feature/20)'
        ),
    )
    parser.add_argument(
        '-m', '--monochrome',
        action='store_true',
        help="Don't use colours in output",
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

    if args.monochrome:
        global style
        style = style_monochrome

    return args


if __name__ == "__main__":
    main()
