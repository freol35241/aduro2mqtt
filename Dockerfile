FROM python:3.11-bullseye

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install --no-cache -r requirements.txt

COPY main.py main.py

CMD ["python3", "main.py"]