from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="entityidentity",
    version="0.0.1",
    author="Peter Cotton",
    author_email="",
    description="Ontology / Entity Resolution",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/petercotton/entityidentity",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        '': ['tables/companies/*.parquet', 'tables/companies/*.csv', 'tables/companies/*.txt'],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "pandas>=1.3.0",
        "rapidfuzz>=2.0.0",
        "pyarrow>=10.0.0",
        "requests>=2.25.0",
    ],
    extras_require={
        "dev": ["pytest>=7.0.0"],
    },
)

