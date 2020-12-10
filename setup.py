'''
Look up packaging instructions from Serious Python to see if anything has changed for Python 3
'''

from setuptools import setup

#this should be pretty detailed; generate from function definitions (i.e. Serious Python)
def readme():
	with open('README.md') as f:
		return f.read()

setup(name='location_search',
	  version='0.1',
	  description='Command line tool for searching location barcodes.',
	  long_description=readme(),
	  #url='https://github.com/ucancallmealicia/utilities',
      license='MIT',
	  author='Alicia Detelich',
	  author_email='adetelich@gmail.com',
      classifiers=[
          'Development Status : : Alpha',
          'License :: OSI Approved :: MIT License'
          'Programming Language :: Python :: 3.7',
          'Natural Language :: English',
          'Operating System :: OS Independent'
          ],
	  entry_points={'console_scripts': ['lookup=location_search.location_search:main']},
	  packages=['location_search'],
	  python_requires='>=3.7',
	  install_requires=['requests', 'utilities @ https://github.com/ucancallmealicia/utilities/tarball/master'],
	  #dependency_links=['git + https://github.com/ucancallmealicia/utilities/tarball/master#egg=utilities-0.1'],
	  include_package_data=True,
	  zip_safe=False)