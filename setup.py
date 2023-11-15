from setuptools import setup, find_packages

setup(
    name='tum',
    version='2.0',
    description='Tinyurl manager',
    packages=find_packages(),
    author_email='',
    author='',
    url='https://github.com/gobbo99/tum-tinyurl/',
    long_description=open('README.md').read(),
    license='MIT',
    install_requires=[
        'requests',
        'terminaltexteffects'
    ],
)
