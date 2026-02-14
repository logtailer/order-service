# FROM python:alpine
# WORKDIR /order-service
# COPY . /order-service
# RUN python3 -m pip install --upgrade pip
# RUN pip install -r requirements.txt
# EXPOSE 5000
# CMD [ "python3", "run.py" ]

FROM python:3.11-slim

WORKDIR /order-service

# Install system deps if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["python3", "run.py"]