from setuptools import find_packages, setup


setup(
    name='djiutil',
    version='0.1.0',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'djiutil = djiutil.__main__:main',
        ]
    }
)
