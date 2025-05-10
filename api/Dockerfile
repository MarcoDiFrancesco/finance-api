# TODO: test on python:3.13-slim once it works stable
FROM python:3.13
WORKDIR /app

# RUN apt-get update && apt-get install ...

COPY requirements.txt .
RUN pip install --no-cache-dir setuptools
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# CMD ["fastapi", "run", "app.py", "--port", "54246"]
CMD ["fastapi", "dev", "app.py", "--host", "0.0.0.0", "--port", "54246"]
