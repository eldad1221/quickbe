import setuptools


with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name="backbone",
    version="0.0.1",
    author="Eldad Bishari",
    author_email="eldad@1221tlv.org",
    description="Backbone infrastructure",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/eldad1221/backbone",
    packages=setuptools.find_packages(),
    install_requires=[
        'flask',
        'waitress',
    ],
    classifiers=[
        "License :: CC",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7  ',
)
