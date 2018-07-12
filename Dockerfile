FROM python:3
ADD requirements.txt requirements.txt
RUN pip install -r requirements.txt
EXPOSE 5000
ADD . .
CMD ["python", "main.py"]