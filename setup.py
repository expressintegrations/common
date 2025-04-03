from setuptools import setup, find_packages

setup(
    name="common",
    version="1.0.0",
    description="Common utilities for Express Integrations",
    packages=find_packages(),
    install_requires=[
        "anvil-uplink==0.4.2",
        "cryptography==43.0.1",
        "dependency-injector==4.43.0",
        "fastapi==0.115.8",
        "firedantic==0.6.0",
        "google-cloud-firestore==2.15.0",
        "google-cloud-logging==3.11.3",
        "google-cloud-run==0.10.0",
        "google-cloud-scheduler==2.13.2",
        "google-cloud-storage==2.14.0",
        "google-cloud-tasks==2.18.0",
        "gunicorn==22.0.0",
        "hubspot-api-client==11.1.0",
        "monday==2.0.0rc3",
        "pydantic==2.10.4",
        "PyJWT==2.10.1",
        "pytz",
        "PyYAML==6.0.1",
        "requests==2.32.3",
        "snowflake-connector-python==3.14.0",
        "starlette",
        "stripe==11.5.0",
        "urllib3==2.2.2",
        "uvicorn==0.27.1",
    ],
)
