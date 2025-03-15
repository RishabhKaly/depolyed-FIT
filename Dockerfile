# FROM python:3.12-slim

# WORKDIR /app

# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy application code
# COPY ./app .

# # Command to run the application
# CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]


# # Use the official Python image as the base
# FROM python:3.12-slim

# # Set the working directory inside the container
# WORKDIR /app

# # Copy and install dependencies
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy the entire application code
# COPY . .

# # Expose the port for FastAPI
# EXPOSE 8000

# # Run FastAPI using Uvicorn
# CMD ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000"]



# Use the official Python 3.12 slim image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy in your requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into /app
COPY . .

# Make /app/app a top-level module path
# so Python can directly import "decorators.py" and "database.py"
ENV PYTHONPATH="/app/app"

# Expose port 8000 for FastAPI
EXPOSE 8000

# Run your FastAPI app (app.py) with Uvicorn on port 8000
# "app:app" means:
#  - "app" is the module name (app.py in /app/app)
#  - "app" is the FastAPI instance inside that file
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

