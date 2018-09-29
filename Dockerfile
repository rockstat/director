FROM rockstat/band-base-py:latest

LABEL maintainer="Dmitry Rodin <madiedinro@gmail.com>"
LABEL band.service.version="0.5.0"
LABEL band.service.title="Director service"
LABEL band.service.def_position="0x0"
LABEL band.service.protected="1"

WORKDIR /usr/src/services

ENV HOST=0.0.0.0
ENV PORT=8080
RUN apt-get update && apt-get install -y --no-install-recommends \
	&& rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE ${PORT}
COPY . .

CMD [ "python", "-m", "director"]
