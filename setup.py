from setuptools import setup
from IPython.core.release import long_description

setup(
    name = "ncobj",
    url='https://github.com/pp-mo/ncobj',
    download_url = 'https://github.com/pp-mo/ncobj/archive/master.zip',
    version = "0.3",
    packages = ['lib/ncobj'],
    author='ppmo',
    author_email='patrick.peglar@metoffice.gov.uk',
    license='GPL',
    description='Python object representation of NetCDF4 data',
    long_description='''\
Allows flexible programmatic handling of NetCDF files.
Enables quick+easy copying of data from one netCDF4 file to another,
with arbitrary changes.
Intended scope similar to NCO commands.'''
)

