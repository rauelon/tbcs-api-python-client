from setuptools import setup, find_packages

setup(
    name='tbcs_api_client',
    version='0.1',
    packages=find_packages(),

    install_requires=['requests>=2.22.0'],

    description="Basic api client for automated testing with TestBench CS",
    license="PSF",
    keywords="testbench tbcs testautomation",
    url="https://testbench.com"
)