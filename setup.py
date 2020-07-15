from setuptools import setup, find_packages

setup(
    name='tbcs_api_client',
    version='0.18',
    packages=find_packages(exclude=['tests']),

    python_requires=">=3.6",
    install_requires=['requests>=2.22.0'],

    description="Basic api client for automated testing with TestBench CS",
    license="PSF",
    keywords="testbench tbcs testautomation",
    url="https://testbench.com"
)
