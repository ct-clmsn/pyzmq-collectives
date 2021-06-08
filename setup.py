#  Copyright (c) 2021 Christopher Taylor
#
#  Distributed under the Boost Software License, Version 1.0. (See accompanying
#  file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
#
from setuptools import setup

setup(name='pyzmqcollectives',
      version='0.1',
      description='SPMD collective communication algorithms using PyZMQ',
      url='https://github.com/ct-clmsn/pyzmq-collectives',
      author='Christopher Taylor',
      author_email='ct.clmsn@gmail.com',
      license='Boost',
      packages=['pyzmqcollectives'],
      install_requires=[
          'zmq',
      ],
      zip_safe=False)
