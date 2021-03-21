import setuptools, re, os.path

def get_property(prop, package):
    dir = os.path.abspath( os.path.dirname(__file__) )
    path = os.path.join(dir, package, '__init__.py')
    with open(path, 'r') as f:
        code = f.read()
        match = re.search(r'{}\s*=\s*[\'"]([^\'"]*)[\'"]'.format(prop), code)
        return match.group(1)

with open('README.md', 'r') as f:
    long_description = f.read()

setuptools.setup(
    name='pdftowrite',
    version=get_property('__version__', 'pdftowrite'),
    author='Космическое П.',
    author_email='kosmospredanie@yandex.ru',
    description='PDF to Write document converter',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/kosmospredanie/pdftowrite',
    license='MIT',
    project_urls={
        'Source': 'https://github.com/kosmospredanie/pdftowrite',
        'Bug Tracker': 'https://github.com/kosmospredanie/pdftowrite/issues',
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'License :: OSI Approved :: MIT License'
    ],
    packages=setuptools.find_packages(),
    package_data={
        'pdftowrite': ['data/*.svg'],
    },
    install_requires=[
        'shortuuid',
    ],
    python_requires='>=3.7',
    entry_points={
        'console_scripts': [
            'pdftowrite=pdftowrite:main',
        ],
    },
)
