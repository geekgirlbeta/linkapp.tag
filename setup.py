from setuptools import setup, find_packages
setup(
    name="linkapp.tag",
    version="0.1",
    packages=["linkapp.tag"],
    install_requires=['redis', 'pika', 'strict_rfc3339', 'jsonschema', 'webob', 'requests']
)