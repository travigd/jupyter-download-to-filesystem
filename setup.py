from setuptools import setup, find_packages

setup(
    name='jupyter-download-to-filesystem',
    version='',
    packages=setuptools.find_packages('.'),
    package_dir={'': '.'},
    install_requires=[
        'notebook',
        'tornado'
    ],
    url='https://github.com/travigd/jupyter-download-to-filesystem',
    license='All Rights Reserved',
    author='Travis G DePrato',
    author_email='travigd@umich.edu',
    description=''
)
