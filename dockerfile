# THIS SCRIPT IS FOR LINUX ONLY

# Use debian-buster base instead of slim
FROM python:3.8-buster

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Update package lists and install dependencies
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# Copy the current directory contents into the container
COPY . .

# Make the script executable
RUN chmod +x script.sh

# Make port 5000 available
EXPOSE 5000

# Run the script when the container launches
CMD ["./script.sh"]



# THIS SCRIPT IS FOR WINDOWS ONLY

# FROM python:3.8-slim-buster

# WORKDIR /app

# # Detect OS and install dos2unix only on Windows
# RUN if [ "$(uname -s)" = "Linux" ] && [ -f /etc/os-release ] && grep -q Microsoft /proc/version; then \
#     # Windows Docker Desktop detected
#     apt-get update && \
#     apt-get install -y dos2unix && \
#     rm -rf /var/lib/apt/lists/*; \
# fi

# COPY script.sh .

# # Handle line endings based on OS
# RUN if command -v dos2unix > /dev/null; then \
#     # Windows: use dos2unix
#     dos2unix script.sh; \
# else \
#     # macOS/Linux: use sed
#     sed -i 's/\r$//' script.sh; \
# fi && \
# chmod +x script.sh

# COPY . .
# EXPOSE 5000

# CMD ["./script.sh"]