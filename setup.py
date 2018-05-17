try:
    from setuptools import setup, find_packages
    print('Cannot find `setuptools`, defaulting to `distutils`')
except ImportError:
    from distutils.core import setup, find_packages

setup(
    name='parking',
    version='0.0.1',
    description='GPIG Project',
    author='GPIG Group E',
    url='https://github.com/educationallylimited/parking',
    packages=find_packages(exclude=('tests')),
)
