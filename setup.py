"""
Setup script for Django Guitar.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="django-guitar",
    version="0.1.0",
    author="Django Guitar Contributors",
    author_email="",
    description="Automatically generate a Django-like ORM for the frontend from your Django models",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/davefowler/django-guitar",
    packages=find_packages(exclude=["example_project", "example_project.*", "tests"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 4.2",
        "Framework :: Django :: 5.0",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.10",
    install_requires=[
        "Django>=4.2,<5.1",
        "django-ninja>=1.0.0,<2.0.0",
        "pydantic>=2.0.0,<3.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-django>=4.5.0",
        ],
    },
)
