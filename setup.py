from setuptools import setup

setup(
    name='wikiextractor',

    description='A script that extracts and cleans text from a Wikipedia'
                'database dump',
    author='Giuseppe Attardi',
    author_email='attardi@di.unipi.it',
    version='2.42',

    url='https://github.com/attardi/wikiextractor',

    license="GPL 3.0",
    keywords=['text', 'nlp'],
    entry_points={
        'console_scripts': [
            'wikiextractor = WikiExtractor:main'
        ]
    }
)
