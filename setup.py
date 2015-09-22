from setuptools import setup, find_packages

setup(
    name='IPS Vagrant',
    version='0.1.0',
    description='A management utility for the (unofficial) Invision Power Suite Vagrant development box.',
    long_description='A management utility for the (unofficial) Invision Power Suite Vagrant development box.',
    author='Makoto Fujimoto',
    author_email='makoto@makoto.io',
    url='https://github.com/FujiMakoto/IPS-Vagrant',
    license='MIT',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'License :: OSI Approved :: MIT License',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: PHP',
        'Topic :: Software Development',
        'Topic :: Software Development :: Code Generators',
        'Topic :: System :: Installation/Setup',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities'
    ],
    packages=find_packages(),
    package_data={'ips_vagrant': ['config/*.conf', 'generators/templates/nginx/*.tpl', 'alembic.ini']},
    entry_points={
        'console_scripts': [
            'ipsv = ips_vagrant.cli:cli'
        ]
    },
    requires=['beautifulsoup4', 'mechanize', 'click', 'requests', 'jinja2', 'alembic', 'sqlahelper', 'progressbar',
              'pyOpenSSL']
)