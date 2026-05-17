"""Setup script for BCB."""

from setuptools import setup, find_packages

setup(
    name="bcb",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'bcb': ['config/*.yaml'],
    },
    install_requires=[
        'typer',
        'rich',
        'pydantic',
        'aiohttp',
        'pyyaml',
    ],
    entry_points={
        'console_scripts': [
            'bcb=bcb.cli:main',
        ],
    },
)
