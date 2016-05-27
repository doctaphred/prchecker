#!/usr/bin/env python3 -u
"""Run some tests (currently just flake8) on all open pull requests!

Reads the following environment variables:

    GITHUB_URL - base url of your GitHub Enterprise instance
    GITHUB_USERNAME - your username on said instance
    GITHUB_TOKEN - an auth token for your account on said instance
    GITHUB_OWNER - the name of the repository owner
    GITHUB_REPO - the name of the repository to check
    WORK_TREE - path to a local clone of the repository
    FLAKE8_PATH - path to a flake8 executable
    FLAKE8_CONFIG_PATH - path to a setup.cfg file

Note that this program requires an existing local clone of the
repository, which may be arbitrarily modified. Don't point it to your
development repo!
"""
import os
from contextlib import contextmanager

from github3 import GitHubEnterprise
from sh import Command, ErrorReturnCode, git


class ItemAttrs:

    def __init__(self, items):
        super().__setattr__('_items', items)

    def __getattr__(self, name):
        return self._items[name]

    def __setattr__(self, name, value):
        self._items[name] = value

    def __delattr__(self, name):
        del self._items[name]


# TODO: ChainMap with sys.argv, setup.cfg, etc.
env = ItemAttrs(os.environ)


@contextmanager
def temp_chdir(path):
    """Change the working directory to <path>, then change it back."""
    original_wd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(original_wd)


def merge_and_check(base, head):
    """Merge <head> into <base>, then run some tests.

    Only modifies the working tree---doesn't actually create a merge
    commit. Resets and cleans the repo and leaves it in headless mode.

    Raises sh.ErrorReturnCode if the merge or the tests fail.
    """
    # Make sure we're up to date
    git.fetch()
    # Make sure we can do a clean checkout
    git.reset(hard=True)
    git.clean('-dfx')
    git.checkout('origin/' + base)
    # Merge the working tree, but don't modify the index
    git.merge('origin/' + head, no_commit=True)
    # Run some tests!
    Command(env.FLAKE8_PATH)('cemt', config=env.FLAKE8_CONFIG_PATH)


def check_open_pull_requests(repo):
    with temp_chdir(env.WORK_TREE):
        for pr in repo.pull_requests(state='open'):
            print('Checking pull request #{}...'.format(pr.number))
            try:
                merge_and_check(pr.base.ref, pr.head.ref)
            except ErrorReturnCode as e:
                print('✘ Problem: {}'.format(e))
            else:
                print('✔ Looks good!')


if __name__ == '__main__':
    gh = GitHubEnterprise(
        env.GITHUB_URL, env.GITHUB_USERNAME, env.GITHUB_TOKEN)
    repo = gh.repository(env.GITHUB_OWNER, env.GITHUB_REPO)
    check_open_pull_requests(repo)
