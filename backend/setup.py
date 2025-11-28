from setuptools import setup, find_packages

setup(
    name='dsa110_contimg',
    version='0.1.0',
    author='Your Name',
    author_email='your.email@example.com',
    description='DSA-110 Continuum Imaging Pipeline',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/dsa110_contimg',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        'numpy',
        'astropy',
        'pyuvdata==3.2.4',
        'pyuvsim',
        'casa6',
        # Add other dependencies as needed
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.11',
)