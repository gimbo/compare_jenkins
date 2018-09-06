#!/usr/bin/env python

import argparse
import os
import sys

import click
import requests
from bs4 import BeautifulSoup


BASE_ENV_VAR_NAME = 'JEN_COMPARE_DEFAULT_BASE'


def main():

    args = parse_args()

    left_branch = branch_url(args.base, args.left)
    right_branch = branch_url(args.base, args.right)
    click.echo('Left branch..: {}'.format(left_branch))
    click.echo('Right branch.: {}'.format(right_branch))
    click.echo()

    left_doc = BeautifulSoup(requests.get(left_branch).content, 'html.parser')
    right_doc = BeautifulSoup(requests.get(right_branch).content, 'html.parser')

    left_failed = get_set_from_html(left_doc)
    right_failed = get_set_from_html(right_doc)
    fail_only_left = sorted(left_failed - right_failed)
    fail_only_right = sorted(right_failed - left_failed)

    click.echo("Failed in the left branch..: {}".format(len(left_failed)))
    click.echo("Failed in the right branch.: {}".format(len(right_failed)))
    click.echo()

    list_side_failures(fail_only_left, left_fail=True, right_fail=False)
    click.echo()
    list_side_failures(fail_only_right, left_fail=False, right_fail=True)


def list_side_failures(failures, left_fail, right_fail):

    pretty = click.style('===', fg='yellow')
    failed = click.style('failed', fg='red')
    passed = click.style('passed', fg='green')

    def side_words(side, failure):
        return '{} {}'.format(side, failed if failure else passed)

    msg = '{pretty} {left_words}, {right_words}: {count} {pretty}'.format(
        pretty=pretty,
        left_words=side_words('left', left_fail),
        right_words=side_words('right', right_fail),
        count=len(failures),
    )
    click.echo(msg)

    for line in failures:
        click.echo(line)


def branch_url(base, path):
    return '{}/{}/testReport/'.format(base, path)


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


def parse_args():
    parser = argparse.ArgumentParser()

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

    args = parser.parse_args()

    if not args.base:
        if default_base:
            args.base = default_base
        else:
            click.echo(
                'No URL base specified (either on command line or env var); '
                'giving up.'
            )
            sys.exit(1)

    return args


if __name__ == "__main__":
    main()
