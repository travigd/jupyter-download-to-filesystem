from setuptools import setup, find_packages

setup(
    name='jupyter-remotefs',
    version='',
    packages=setuptools.find_packages('.'),
    package_dir={'': '.'},
    install_requires=[
        'notebook',
        'tornado'
    ],
    url='https://github.com/travigd/jupyter-remotefs',
    license='All Rights Reserved',
    author='Travis G DePrato',
    author_email='travigd@umich.edu',
    description=''
)
