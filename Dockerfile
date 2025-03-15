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



# Use the official Python image
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Ensure Python recognizes `app/` as a package
RUN touch /app/app/__init__.py

# Set PYTHONPATH so Python knows where to find modules
ENV PYTHONPATH="/app"

# Expose the port for FastAPI
EXPOSE 8000

# Run FastAPI with Uvicorn
CMD ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000"]
