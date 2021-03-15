from setuptools import setup, find_packages

setup(
    name='tbcs_api_client',
    version='0.22',
    packages=find_packages(exclude=['tests']),

    python_requires=">=3.8",
    install_requires=['requests>=2.25.1'],

    description="Basic api client for automated testing with TestBench CS",
    license="PSF",
    keywords="testbench tbcs testautomation",
    url="https://testbench.com"
)
