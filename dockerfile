FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . .

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
# RUN pip install -r requirements.txt

# Install playwright after installing Python dependencies
RUN python -m playwright install

# Make port 5000, 5432 available to the world outside this container
EXPOSE 5000
EXPOSE 5432


CMD ["python", "run.py", "playwright install"]
