# Minimal Dockerfile for CI environment simulation
# Matches GitHub Actions ubuntu-latest runner with Python 3.11
#
# This image is used to simulate the exact CI environment locally.
# It allows developers to run `make test-ci` to catch environment-specific issues
# (symlinks, permissions, paths) before pushing to GitHub Actions.

FROM python:3.11-slim

# Install system dependencies needed by the test suite
# - git: for version detection and symlink support
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set up git symlink support (matches CI configuration)
RUN git config --global core.symlinks true

# Create working directory
WORKDIR /workspace

# Copy entire repository into the container
COPY . .

# Install Python dependencies (from setup.py)
RUN pip install --upgrade pip && \
    pip install pytest pytest-cov pyyaml && \
    pip install -e .

# Set environment variable for pytest
ENV PYTHONPATH=/workspace:${PYTHONPATH}

# Health check: verify framework files exist
RUN test -f /workspace/src/AGENTS.md && test -f /workspace/src/SKILLS.md && python -c "print('✓ Framework files verified')"

# Default command: run tests
CMD ["pytest", "tests/", "-v", "--tb=short"]
