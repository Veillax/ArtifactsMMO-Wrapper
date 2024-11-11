from setuptools import setup, find_packages

setup(
    name="artifacts_mmo",
    version="0.1.0",
    author="Veillax",
    author_email="contact@veillax.com",
    description="A Python API Wrapper for ArtifactsMMO",
    url="https://github.com/Veillax/ArtifactsMMO-S3-Wrapper", 
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Affero General Public License  v3 (AGPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11.7",
    install_requires=[
        "requests"
    ],
)
