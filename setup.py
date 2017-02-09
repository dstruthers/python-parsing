from setuptools import setup

import parsing

setup(name='parsing',
      version=parsing.__version__,
      author='Darren M. Struthers',
      author_email='dstruthers@gmail.com',
      py_modules=['parsing'],
      description='Combinatorial parsing framework',
      license='MIT',
      install_requires=['typefu']
      )
