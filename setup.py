import re
from setuptools import setup

with open("readme.md") as f:
    readme = f.read()

requirements = ['sly', 'matplotlib']

with open('mathparser/__init__.py') as f:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.MULTILINE).group(1)

setup(name='discord.py',
      author='IAmTomahawkx',
      url='https://github.com/IAmTomahawkx/math-parser',
      project_urls={
        "Issue tracker": "https://github.com/IAmTomahawkx/math-parser/issues",
      },
      version=version,
      packages=["mathparser"],
      license='MIT',
      description="A math expression parser that uses AST to parse equations",
      long_description=readme,
      long_description_content_type="text/markdown",
      include_package_data=True,
      install_requires=requirements,
      python_requires='>=3.7.0',
      classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Internet',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',
      ]
)