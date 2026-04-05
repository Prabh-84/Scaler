
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
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Node.js (for Next.js)
RUN apt-get update && apt-get install -y nodejs npm

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# Install frontend deps + build
WORKDIR /app/chaos-frontend
RUN npm install
RUN npm run build

WORKDIR /app

EXPOSE 7860

# 🔥 IMPORTANT: run frontend + backend together
CMD sh -c "npm --prefix chaos-frontend start & uvicorn app:app --host 0.0.0.0 --port 7860"