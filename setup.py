import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="simplesox8",
    version="0.0.1",
    description="Socket Server is a simple TCP Socket server and client.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/charliepilot/socket_server",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
