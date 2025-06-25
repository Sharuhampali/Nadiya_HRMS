
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install dependencies required for psycopg2 and other common packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirement files first (for caching layer)
COPY requirements.txt .


# Install Python dependencies
RUN pip install --upgrade pip \
    && pip install gunicorn \
    && pip install Cython \
    && pip install -r requirements.txt

# Copy project files
COPY . .

EXPOSE 8080

CMD ["gunicorn", "-b", "0.0.0.0:8080", "main:app"]

