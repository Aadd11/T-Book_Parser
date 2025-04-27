# Use official Python 3.11 image
FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV ARGOS_PACKAGES_DIR=/usr/local/lib/python3.11/site-packages/argostranslate/packages

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Copy requirements
COPY requirements-docker.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements-docker.txt

# Install Argos Translate language packs (updated method)
RUN python -c "from argostranslate import package; package.update_package_index(); \
    installed_packages = package.get_installed_packages(); \
    available_packages = package.get_available_packages(); \
    [package.install_from_path(pkg.download()) for pkg in available_packages \
    if pkg.from_code == 'en' and pkg.to_code == 'ru' and \
    not any(inst.from_code == pkg.from_code and inst.to_code == pkg.to_code for inst in installed_packages)]"

# Copy application code
COPY . .

# Expose port
EXPOSE 5000

# Run with Waitress
CMD ["waitress-serve", "--port=5000", "app:app"]