FROM ahmad88me/ome:latest
WORKDIR /app
COPY data data
COPY templates templates
COPY *.py /app/
#COPY requirements.txt /app/
#RUN pip install -r requirements.txt
CMD ["python", "app.py", "0.0.0.0", "5000"]