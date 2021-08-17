from setuptools import setup

setup(
    name='proto_extractor',
    version='0.1.0',
    py_modules=['proto_extractor'],
    install_requires=[
        'protobuf',
    ],
    entry_points = {
        'console_scripts': ['proto_extractor=proto_extractor:extract_cli'],
    }
)