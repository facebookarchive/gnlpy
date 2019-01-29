# Contributing to gnlpy
We want to make contributing to this project as easy and transparent as
possible.

## Our Development Process
We develop on a private branch internally at Facebook. We regularly update
this github project with the changes from the internal repo. External pull
requests are cherry-picked into our repo and then pushed back out.

## Pull Requests
We actively welcome your pull requests.
1. Fork the repo and create your branch from `master`.
2. If you've added code that should be tested, add tests
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes (`nosetests -v --with-coverage --cover-erase .`).
5. Make sure your code lints. (`flake8 .`)
6. If you haven't already, complete the Contributor License Agreement ("CLA").

### Development environment

In order to make it easier to test the code in an isolated environment, one can
use [vagrant](https://www.vagrantup.com/).

A `Vagranfile` is available at the root of the repository. The VM can be spinned
up using:

`vagrant up`

On the first run, the VM will be provisioned with all the necessary dependencies
to run the unittests suites.

To run the test suites use:
`vagrant ssh -c 'sudo bash -c "cd /mnt/gnlpy; nosetests -v --with-coverage --cover-erase ."'`

To run the linter:
`vagrant ssh -c 'sudo bash -c "cd /mnt/gnlpy; flake8 ."'`


## Contributor License Agreement ("CLA")
In order to accept your pull request, we need you to submit a CLA. You only need
to do this once to work on any of Facebook's open source projects.

Complete your CLA here: <https://code.facebook.com/cla>

## Issues
We use GitHub issues to track public bugs. Please ensure your description is
clear and has sufficient instructions to be able to reproduce the issue.

Facebook has a [bounty program](https://www.facebook.com/whitehat/) for the safe
disclosure of security bugs. In those cases, please go through the process
outlined on that page and do not file a public issue.

## Coding Style
Please adhere to [PEP 8](https://www.python.org/dev/peps/pep-0008/) whenever possible.

## License
By contributing to gnlpy, you agree that your contributions will be licensed
under its BSD license.
