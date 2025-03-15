# FROM python:3.12-slim

# WORKDIR /app

# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy application code
# COPY ./app .

# # Command to run the application
# CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.9

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# COPY ./app /code/app

COPY ./sample /code/sample

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]