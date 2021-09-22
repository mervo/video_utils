from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
        name='video-utils', 
        version='1.0', 
        description="DH video utility module",
        long_description=long_description,
        long_description_content_type="text/markdown",
        classifiers=[
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
        ],
        packages=find_packages(exclude=("test",)),
    )
