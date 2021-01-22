from setuptools import setup, find_packages

setup(
    name='reactivetools',
    version='0.1',
    packages=find_packages(),
    install_requires=['pyelftools==0.27', 'aiofile==3.3.3'],
    entry_points={
        'console_scripts': ['reactive-tools = reactivetools.cli:main']
    },

    author='Job Noorman',
    author_email='job.noorman@cs.kuleuven.be'
)
