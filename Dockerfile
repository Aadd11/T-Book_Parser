FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV ARGOS_PACKAGES_DIR=/usr/local/lib/python3.11/site-packages/argostranslate/packages

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev libgomp1 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Install Argos Translate packages
RUN python -c "from argostranslate import package; \
    package.update_package_index(); \
    [package.install_from_path(pkg.download()) \
    for pkg in package.get_available_packages() \
    if pkg.from_code == 'en' and pkg.to_code == 'ru']"

COPY . .

EXPOSE 5000

# Using waitress with factory pattern
CMD ["waitress-serve", "--port=5000", "--call", "app:create_app"]