FROM python:3.8-slim

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the rest of the application
COPY . .

# Create database and tables before starting the app (optional)
# Note: This might not work as expected if your app requires a running database or environment variables
# RUN python app.py

CMD ["python", "app.py"]
