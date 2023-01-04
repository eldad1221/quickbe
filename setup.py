import setuptools


with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name="quickbe",
    version="4.2.0",
    author="Eldad Bishari",
    author_email="eldad@1221tlv.org",
    description="Quick and simple back-end infrastructure",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/eldad1221/quickbe",
    packages=setuptools.find_packages(),
    install_requires=[
        'flask==2.0.1',
        'cerberus==1.3.4',
        'schedule==1.1.0',
        'psutil==5.9.4',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
