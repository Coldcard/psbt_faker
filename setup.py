# based on <http://click.pocoo.org/5/setuptools/#setuptools-integration>
#
# To use this, install with:
#
#   pip install --editable .

from setuptools import setup

setup(
    name='psbt_faker',
    version='1.0',
    py_modules=[],
    python_requires='>3.6.0',
    install_requires=[
        'Click',
    ],
    entry_points='''
        [console_scripts]
        psbt_faker=main:faker
    ''',
)

