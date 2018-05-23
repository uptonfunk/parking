# parking

[![Build Status](https://travis-ci.com/educationallylimited/parking.svg?branch=master)](https://travis-ci.com/educationallylimited/parking)
[![Coverage Status](https://coveralls.io/repos/github/educationallylimited/parking/badge.svg?branch=master)](https://coveralls.io/github/educationallylimited/parking?branch=master)

Parking monolith

## Installing requirements

    $ python3 -m pip install -r requirements.txt

## Linting

Flake8 is used for style enforcement / static analysis. Usage is simple,
navigate to the project directory then:

   $ python3 -m flake8 .

  
## Running tests

First, make sure you have a virtualenv and install it:

	$ python3 -m venv venv
	$ venv/bin/pip install -r requirements.txt
	
	
Then run pytest

	$ venv/bin/pytest .