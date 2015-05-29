import forseti

from setuptools import setup, find_packages


setup(
    name='forseti',
    version=forseti.__version__,
    description="Manage your AWS autoscaling groups and policies and create AMIs for autoscaling purposes",
    long_description=open('README.md').read(),
    install_requires=[
        'blessings',
        'docopt',
        'boto',
        'jinja2',
        'paramiko',
        'progressbar',
    ],
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
    author='ticketea',
    author_email='dev@ticketea.com',
    url='http://github.com/ticketea/forseti',
    license='BSD',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)
