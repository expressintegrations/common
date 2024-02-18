from setuptools import setup, find_packages

setup(
    name='growth-ops-apps-common',
    version='1.0.0',
    description='Common utilities for Growth Ops Apps',
    packages=find_packages(),
    install_requires=[
        'anvil-uplink==0.4.2',
        'dependency-injector==4.41.0',
        'fastapi==0.104.0',
        'google-cloud-firestore==2.10.0',
        'google-cloud-logging==3.5.0',
        'google-cloud-run==0.10.0',
        'google-cloud-tasks==2.13.1',
        'gunicorn==20.1.0',
        'hubspot-api-client==8.0.0',
        'pydantic==2.4.2',
        'PyJWT==2.7.0',
        'pytz',
        'requests==2.31.0',
        'starlette==0.27.0',
        'stripe~=5.2.0',
        'urllib3==1.26.14',
        'uvicorn==0.22.0'
    ],
)
