# Use an official Python runtime image
FROM python:3.11-slim

# Set working directory in the container
WORKDIR /app

# Set environment variables
# Prevent Python from writing .pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1
# Prevent Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

# Copy requirements file first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY app ./app

# Expose the default FastAPI port
EXPOSE 8000

# Default command to run the Uvicorn server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
