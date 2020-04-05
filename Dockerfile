FROM oegupm/ome:latest
WORKDIR /app
COPY data data
COPY templates templates
COPY *.py /app/
RUN mkdir -p /app/upload
#COPY requirements.txt /app/
#RUN pip install -r requirements.txt
CMD ["python", "app.py", "0.0.0.0", "5000"]
