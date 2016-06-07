import os
from setuptools import setup

import telegram_bot

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name="telegram_aegee_bot",
    version=telegram_bot.__version__,
    author=telegram_bot.__author__,
    author_email=telegram_bot.__email__,
    description=("Telegram Bot for AEGEE, serves for events expecially Agoras"),
    license="Apache",
    keywords="telegram aegee bot agora events",
    url="https://github.com/AEGEE/telegram-aegee-bot",
    packages=['telegram_bot', 'tests'],
    long_description=read('README.md'),
    install_requires=[
        'python-telegram-bot',
        'argparse',
        'configparser'
    ],
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: Apache Software License",
    ],
    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        'console_scripts': [
            'telegram_bot=telegram_bot.main:main',
        ],
    },
)