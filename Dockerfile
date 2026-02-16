# FROM python:alpine
# WORKDIR /order-service
# COPY . /order-service
# RUN python3 -m pip install --upgrade pip
# RUN pip install -r requirements.txt
# EXPOSE 5000
# CMD [ "python3", "run.py" ]

# Build stage
FROM python:3.11-slim AS builder

WORKDIR /install

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir wheel
RUN pip wheel --no-cache-dir --wheel-dir=/install/wheels -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /order-service

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder stage and install
COPY --from=builder /install/wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# Copy only necessary files
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY run.py manage.py entrypoint.sh ./

# Set permissions and configuration
RUN chmod +x /order-service/entrypoint.sh

EXPOSE 5000

ENTRYPOINT ["/order-service/entrypoint.sh"]
CMD ["app"]