# Setup configuration for baggage operations platform
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="baggage-ops-platform",
    version="1.0.0",
    author="Number Labs",
    author_email="jp@numberlabs.ai",
    description="AI-Powered Baggage Intelligence Platform for Airlines",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jbandu/bag",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Airlines",
        "Topic :: Software Development :: AI Systems",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.11",
    install_requires=[
        "langchain>=0.3.1",
        "langchain-anthropic>=0.2.1",
        "langgraph>=0.2.28",
        "anthropic>=0.39.0",
        "streamlit>=1.39.0",
        "fastapi>=0.115.4",
        "uvicorn[standard]>=0.32.0",
        "pydantic>=2.9.2",
        "pydantic-settings>=2.6.0",
        "neo4j>=5.25.0",
        "supabase>=2.9.0",
        "psycopg2-binary>=2.9.9",
        "redis>=5.2.0",
        "pandas>=2.2.3",
        "numpy>=2.1.3",
        "xmltodict>=0.14.2",
        "lxml>=5.3.0",
        "python-dotenv>=1.0.1",
        "httpx>=0.27.2",
        "loguru>=0.7.2",
        "plotly>=5.24.1",
    ],
    extras_require={
        "dev": [
            "pytest>=8.3.3",
            "pytest-asyncio>=0.24.0",
            "pytest-cov>=5.0.0",
            "black>=24.10.0",
            "ruff>=0.7.3",
            "mypy>=1.13.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "baggage-api=api_server:main",
            "baggage-dashboard=dashboard.app:main",
        ],
    },
)
