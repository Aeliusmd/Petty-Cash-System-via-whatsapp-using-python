FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY backend/ ./backend/
COPY run.py .
COPY .env* ./

# Set Python path
ENV PYTHONPATH=/app/backend

# Expose port
EXPOSE 4101

# Run with uvicorn
CMD ["python", "run.py"]
