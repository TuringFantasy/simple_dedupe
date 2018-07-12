FROM python:3
ADD . .
RUN pip install -r requirements.txt
EXPOSE 5000
CMD ["python", "main.py"]