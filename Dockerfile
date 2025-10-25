# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements-pinecone.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-pinecone.txt

# Copy application code
COPY . .

# Expose the port that Cloud Run will use
EXPOSE 8001

# Set environment variables
ENV PORT=8001
ENV HOST=0.0.0.0

# Run the application using the main.py entry point
# Cloud Run will set PORT environment variable
CMD ["python", "main.py"]
