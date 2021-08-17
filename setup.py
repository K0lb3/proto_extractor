from setuptools import setup

setup(
    name='protoex',
    version='0.1.0',
    py_modules=['protoex'],
    install_requires=[
        'protobuf',
    ],
    entry_points = {
        'console_scripts': ['protoex=protoex:extract_cli'],
    }
)