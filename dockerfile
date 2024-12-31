# FROM python:3.8-slim

# # Set the working directory
# WORKDIR /app

# # Install necessary packages
# RUN apt-get update && apt-get install -y \
#     file \
#     dos2unix \
#     && rm -rf /var/lib/apt/lists/*

# # Copy requirements first
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy the script and set permissions
# COPY script.sh .
# RUN dos2unix script.sh && chmod +x script.sh

# # Copy the rest of the application
# COPY . .

# # Make port 5000 available
# EXPOSE 5000


# # Run the script when the container launches
# CMD ["./script.sh"]


FROM python:3.8-slim-buster

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Detect OS and install dos2unix only on Windows
RUN if [ "$(uname -s)" = "Linux" ] && [ -f /etc/os-release ] && grep -q Microsoft /proc/version; then \
    # Windows Docker Desktop detected
    apt-get update && \
    apt-get install -y dos2unix && \
    rm -rf /var/lib/apt/lists/*; \
fi

COPY script.sh .

# Handle line endings based on OS
RUN if command -v dos2unix > /dev/null; then \
    # Windows: use dos2unix
    dos2unix script.sh; \
else \
    # macOS/Linux: use sed
    sed -i 's/\r$//' script.sh; \
fi && \
chmod +x script.sh

COPY . .
EXPOSE 5000

CMD ["./script.sh"]