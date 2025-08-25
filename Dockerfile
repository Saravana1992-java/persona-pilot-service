# Use an official Python runtime as a parent image
FROM harbor.hpc.ford.com/python-coe/python-ub:3.10-latest

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Copy the requirements.txt file into the container
COPY requirements.txt /app/

RUN pip install --upgrade pip

RUN pip install --no-cache-dir -r requirements.txt

# Copy the app directory contents into the container at /app
COPY src /app/src

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Run the command to start uvicorn
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080", "--log-level", "info"]