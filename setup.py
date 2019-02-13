from distutils.core import setup


with open('requirements.txt') as fp:
    install_requires = fp.read()

setup(
    name='compare-jenkins',
    version='0.1',
    url='https://github.com/evilkost/compare_jenkins',
    author='Valentin Gologuzov',
    description='Simple script to compare test results in jenkins.',
    install_requires=install_requires,
    entry_points={
        'console_scripts': [
            'jen-compare=jen_compare:main',
        ],
    },
)
