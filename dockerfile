FROM python:3.8-slim

# Set the working directory
WORKDIR /app

# Install necessary packages
RUN apt-get update && apt-get install -y \
    file \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the script and set permissions
COPY script.sh .
RUN dos2unix script.sh && chmod +x script.sh

# Copy the rest of the application
COPY . .

# Make port 5000 available
EXPOSE 5000

# Run the script when the container launches
CMD ["./script.sh"]
