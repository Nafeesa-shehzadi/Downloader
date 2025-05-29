FROM python:3.9-slim

# Install ffmpeg and other dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create temp downloads directory
RUN mkdir -p temp_downloads && chmod 777 temp_downloads

# Expose the port the app runs on
EXPOSE 8080

# Update the Flask app to run on the correct host and port for Railway
ENV PORT=8080
ENV HOST=0.0.0.0

# Run the application
CMD gunicorn --bind $HOST:$PORT app:app
