from setuptools import setup

setup(
	name='RcGcDw',
	version='1.14.0.1',
	packages=[''],
	url='https://gitlab.com/piotrex43/RcGcDw/',
	license='GNU GPLv3',
	author='Frisk',
	author_email='piotrex43@protonmail.ch',
	description='A set od scripts to fetch recent changes from MediaWiki wiki to a Discord channel using a webhook',
	keywords=['MediaWiki', 'recent changes', 'Discord', 'webhook'],
	package_dir={"": "src"},
	install_requires=["beautifulsoup4 >= 4.6.0", "requests >= 2.18.4", "schedule >=  0.5.0", "lxml >= 4.2.1"],
	python_requires="3.7"
)
