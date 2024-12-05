from setuptools import setup, find_packages

setup(
    name="bluesky-archiver",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "websockets",
        "atproto",
        "aiofiles"
    ],
) 