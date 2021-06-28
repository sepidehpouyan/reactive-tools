import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="reactive-tools",
    version="0.2.1",
    author="Gianluca Scopelliti",
    author_email="gianlu.1033@gmail.com",
    description="Deployment tools for the Authentic Execution framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gianlu33/reactive-tools",
    packages=setuptools.find_packages(),
    install_requires=[
        'pyelftools==0.27',
        'aiofile==3.3.3',
        'pycryptodome==3.10.1',
        'reactive-net==0.2',
        'rust-sgx-gen==0.1.3',
        'PyYAML==5.4.1'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    include_package_data=True,
    entry_points={
        'console_scripts': ['reactive-tools = reactivetools.cli:main']
    }
)
