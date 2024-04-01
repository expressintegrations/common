from setuptools import setup, find_packages

setup(
    name='common',
    version='1.0.0',
    description='Common utilities for Express Integrations',
    packages=find_packages(),
    install_requires=[
        'anvil-uplink==0.4.2',
        'cryptography==42.0.5',
        'dependency-injector==4.41.0',
        'fastapi==0.110.0',
        'firedantic==0.6.0',
        'google-cloud-firestore==2.15.0',
        'google-cloud-logging==3.5.0',
        'google-cloud-run==0.10.0',
        'google-cloud-scheduler==2.13.2',
        'google-cloud-storage==2.14.0',
        'google-cloud-tasks==2.13.1',
        'gunicorn==21.2.0',
        'hubspot-api-client==8.2.1',
        'monday==2.0.0rc3',
        'pydantic==2.6.3',
        'PyJWT==2.8.0',
        'pytz',
        'PyYAML==6.0.1',
        'requests==2.31.0',
        'snowflake-connector-python==3.7.1',
        'starlette==0.36.3',
        'stripe~=5.2.0',
        'urllib3==2.2.1',
        'uvicorn==0.27.1'
    ],
)
