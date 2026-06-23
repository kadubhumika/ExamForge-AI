# 1. Use an official, lightweight Python runtime base image
FROM python:3.11-slim

# 2. Set system environment configurations
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Create and set the operational inside directory
WORKDIR /app

# 4. Install system dependencies needed for compiling certain python tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 5. Copy dependency list and install requirements
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 6. Copy the rest of the application codebase
COPY . /app/

# 7. Expose the standard FastAPI backend port
EXPOSE 8085

# 8. Production execution entrypoint script command
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "1000"]
