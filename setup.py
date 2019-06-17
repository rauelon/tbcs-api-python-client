from setuptools import setup, find_packages

setup(
    name='tbcs_api_client',
    version='0.9',
    packages=find_packages(),

    install_requires=['requests'],

    description="Basic api client for automated testing with TestBench CS",
    license="PSF",
    keywords="testbench tbcs testautomation",
    url="https://testbench.com"
)
