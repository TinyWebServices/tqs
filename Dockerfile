FROM python:3.6

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

RUN mkdir /data
VOLUME /data

EXPOSE 8080
CMD [ "python", "tqs.py" ]
