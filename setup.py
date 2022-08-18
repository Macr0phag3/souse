import setuptools


with open("README.md", "r") as fh:
    long_description = "".join(fh.readlines()[:-4])

setuptools.setup(
    name="souse",
    version="3.2.2",
    author="Tr0y",
    author_email="macr0phag3@qq.com",
    description="A tool for converting Python source code to opcode(pickle)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Macr0phag3/souse",
    packages=["souse"],
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=["colorama"],
    python_requires='>=3.6',
    entry_points={
        "console_scripts": [
            'souse = souse:cli',
        ]
    }
)
