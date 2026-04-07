
# FROM python:3.10-slim

# ENV PYTHONDONTWRITEBYTECODE=1
# ENV PYTHONUNBUFFERED=1

# WORKDIR /app

# COPY requirements.txt /app/requirements.txt
# RUN pip install --no-cache-dir --upgrade pip && \
#     pip install --no-cache-dir -r /app/requirements.txt

# COPY . /app

# EXPOSE 7860

# CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
FROM python:3.10.16-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Node.js
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs

WORKDIR /app

# Install backend dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy project
COPY . /app

# 🔥 FRONTEND BUILD (STATIC EXPORT)
WORKDIR /app/chaos-frontend
RUN npm install
RUN npm run build


# Back to root
WORKDIR /app

EXPOSE 7860

# ✅ ONLY backend runs (frontend will be served statically)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]