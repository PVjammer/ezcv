import os
import sys

from setuptools import setup, find_packages

def iter_protos(parent=None):
    for root, _, files in os.walk('proto'):
        if not files:
            continue
        dest = root if not parent else os.path.join(parent, root)
        yield dest, [os.path.join(root, f) for f in files]

pkg_name = 'vidstreamer'

setup(name=pkg_name, 
        package_dir={
            '':'lang/python',
            },
        version='0.1.0',
        description='Protocol wrapper for streaming video analytics',
        author='Nick Burnett',
        author_email='nicholas.c.burnett@gmail.com',
        url='github.com/pvjammer/vidstreamer',
        license='Apache License, Version 2.0',
        packages=["vidstreamer"],
        install_requires=[
          'setuptools>=41.0.0',
          'protobuf>=3.6.1',
          'googleapis-common-protos>=1.6.0',
          'Click>=7.0',
          'dataclasses>=0.6',
          'six>=1.12.0',
          'requests>=2.0.0',
          'flask>=1.0.0',
          'influxdb~=5.2.3',
          'opencv-python>=4.2.0.0'
          'numpy>=1.18.0'
            ],
        data_files=list(iter_protos(pkg_name)),
        py_modules = [
            'vidstreamer.analytic_pb2',
            'vidstreamer.__init__'
            ])

