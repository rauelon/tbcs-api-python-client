from setuptools import setup, find_packages

setup(
    name='tbcs_api_client',
    version='0.11',
    packages=find_packages(exclude=['tests']),

    install_requires=['requests', 'urllib3'],

    description="Basic api client for automated testing with TestBench CS",
    license="PSF",
    keywords="testbench tbcs testautomation",
    url="https://testbench.com"
)
