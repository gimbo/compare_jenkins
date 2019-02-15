from distutils.core import setup


with open("requirements.txt") as fp:
    install_requires = fp.read()

setup(
    name="gentle-jenkins-tools",
    version="0.1",
    url="https://github.com/gimbo/gentle-jenkins-tools",
    author="Andy Gimblett",
    description="Some small Jenkins-related tools which I sometimes find useful",
    install_requires=install_requires,
    entry_points={
        "console_scripts": [
            "jen-compare=jen_compare:main",
            "jen-job-history=jen_job_history:main",
        ]
    },
)
