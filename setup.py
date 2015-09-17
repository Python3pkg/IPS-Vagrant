from setuptools import setup, find_packages

setup(
    name='IPS Vagrant',
    version='0.1.0',
    description='IPS Vagrant',
    long_description='IPS Vagrant',
    author='Makoto Fujimoto',
    author_email='makoto@makoto.io',
    url='https://github.com/FujiMakoto/IPS-Vagrant',
    license='MIT',
    classifiers=[
        'Development Status :: 1 - Planning',
        'License :: OSI Approved :: MIT License',
    ],
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'ipsv = ips_vagrant.cli:cli'
        ]
    },
    requires=['beautifulsoup4', 'mechanize', 'click', 'requests']
)