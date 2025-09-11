#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup script for WalletSender Modular
"""

from setuptools import setup, find_packages
from pathlib import Path

# Читаем версию из модуля
version_file = Path("src/wallet_sender/__init__.py")
version = "2.4.20"
if version_file.exists():
    with open(version_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('__version__'):
                version = line.split('=')[1].strip().strip('"').strip("'")
                break

# Читаем README
readme_file = Path("README.md")
long_description = "WalletSender Modular - Advanced DeFi Wallet Management Tool"
if readme_file.exists():
    with open(readme_file, 'r', encoding='utf-8') as f:
        long_description = f.read()

setup(
    name="walletsender-modular",
    version=version,
    description="WalletSender Modular - Advanced DeFi Wallet Management Tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="WalletSender Team",
    author_email="support@walletsender.dev",
    url="https://github.com/walletsender/walletsender-modular",
    license="MIT",
    packages=find_packages("src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
    install_requires=[
        "PyQt5>=5.15.9",
        "web3>=6.11.0", 
        "requests>=2.31.0",
        "aiohttp>=3.8.5",
        "asyncio-throttle>=1.0.2",
        "cryptography>=41.0.0",
        "eth-account>=0.9.0",
        "eth-utils>=2.2.0",
        "pandas>=2.1.0",
        "numpy>=1.24.0",
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0.1",
        "sqlalchemy>=2.0.0",
        "alembic>=1.12.0",
        "qasync>=0.24.0",
        "qdarkstyle>=3.2.3",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-qt>=4.2.0",
            "mypy>=1.5.0",
            "pylint>=3.0.0",
            "black>=23.7.0",
            "isort>=5.12.0",
            "pyinstaller>=5.13.2"
        ]
    },
    entry_points={
        "console_scripts": [
            "walletsender=wallet_sender.__main__:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers", 
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries",
        "Topic :: Office/Business :: Financial",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
    ],
    include_package_data=True,
    zip_safe=False,
)
