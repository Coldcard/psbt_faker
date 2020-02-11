# based on <http://click.pocoo.org/5/setuptools/#setuptools-integration>
#
# To use this, install with:
#
#   pip install --editable .

from setuptools import setup, find_packages

VERSION = '1.1'

with open('README.md', 'rt') as fd:
    desc = fd.read()

if __name__ == '__main__':
    setup(
        name='psbt_faker',
        author='Coinkite Inc.',
        author_email='support@coinkite.com',
        description="Constructs a valid PSBT files which spend non-existant BTC to random addresses",
        version=VERSION,
        packages=find_packages(),
        long_description=desc,
        long_description_content_type="text/markdown",
        url="https://github.com/Coldcard/psbt_faker",
        py_modules=['psbt_faker'],
        python_requires='>3.6.0',
        install_requires=[
            'Click',
            'pycoin==0.80',
        ],
        entry_points='''
            [console_scripts]
            psbt_faker=psbt_faker:faker
        ''',
        classifiers=[
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
        ]
    )

