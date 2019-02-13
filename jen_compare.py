#!/usr/bin/env python

import argparse
import os
import sys

import click
import requests
from bs4 import BeautifulSoup
from click import echo


try:
    import http.client as httplib
except ImportError:
    import httplib


BASE_ENV_VAR_NAME = 'JEN_COMPARE_DEFAULT_BASE'
DEFAULT_TIMEOUT = 5  # Seconds


def main():

    args = parse_args()

    left_branch = branch_url(args.base, args.left)
    right_branch = branch_url(args.base, args.right)
    echo('Left branch..: {}'.format(left_branch))
    echo('Right branch.: {}'.format(right_branch))
    echo()

    left_doc = get_url(left_branch, timeout=args.timeout)
    right_doc = get_url(right_branch, timeout=args.timeout)

    left_failed = get_set_from_html(left_doc)
    right_failed = get_set_from_html(right_doc)
    fail_only_left = sorted(left_failed - right_failed)
    fail_only_right = sorted(right_failed - left_failed)

    echo("Failed in the left branch..: {}".format(len(left_failed)))
    echo("Failed in the right branch.: {}".format(len(right_failed)))
    echo()

    list_side_failures(fail_only_left, left_fail=True, right_fail=False)
    echo()
    list_side_failures(fail_only_right, left_fail=False, right_fail=True)


def branch_url(base, path):
    return '{}/{}/testReport/'.format(base, path)


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
    return BeautifulSoup(response.content, 'html.parser')


def get_set_from_html(html):
    """
    :param html: Parsed BS html
    :return: set of failing tests names
    """
    fail_table = html.find_all('table')[1]
    failed = set()
    for row in fail_table.find_all('tr')[1:]:
        failed.add(row.find_all('a')[2].text)

    return failed


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

    for line in failures:
        echo(line)


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
