from setuptools import setup, find_packages

setup(
    name="multi_domain_ner",
    version="1.0.0",
    description="Multi-Domain Entity Extraction for Legal and Medical Documents",
    author="Your Name",
    python_requires=">=3.10",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "torch>=2.2.0",
        "transformers>=4.38.2",
        "spacy>=3.7.4",
        "fastapi>=0.110.0",
        "pyyaml>=6.0.1",
    ],
    extras_require={
        "dev": ["pytest", "pytest-cov", "black", "isort", "flake8"],
    },
)
