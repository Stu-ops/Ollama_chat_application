FROM python:3.9-slim

WORKDIR /app

# Install Python dependencies only
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your Flask/Socket.IO app
COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
