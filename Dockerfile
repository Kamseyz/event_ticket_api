FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*



# Set the working directory BEFORE copying anything.
# WORKDIR used to come last, so `COPY . .` dropped the code into / and left
# /app empty -- hence "can't open file '/app/manage.py'".
WORKDIR /app

#copy requiremnets
COPY requirements.txt .

#RUN THE CODE
RUN pip install --no-cache-dir -r requirements.txt

#COPY THE CODE
COPY . .

