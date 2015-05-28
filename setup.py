import imp
import forseti

from setuptools import setup, find_packages

metadata = imp.load_source('metadata', 'forseti/metadata.py')

setup(
    author=metadata.__author__,
    author_email=metadata.__email__,
    url=metadata.__url__,
    license=metadata.__license__,
    name=metadata.__uname__,
    version=metadata.__version__,
    description=metadata.__long_name__,
    long_description=open('README.md').read(),
    install_requires=[[req.strip() for req in open('requirements/base.txt').readlines()]],
    entry_points={
        'console_scripts': [
            'forseti = forseti.bin.cli:main'
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: Site Management",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
    ],
    keywords=['AWS', 'EC2', 'forseti', 'boto', 'AMI'],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)
