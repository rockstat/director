# RST Director

## Running

### Local with watching

#### Run Redis

Containers interract via redis pub-sub.

```
docker run -d \
    --restart unless-stopped \
    --network custom \
    --name redis --hostname redis \
    -p 127.0.0.1:6379:6379 \
    redis:4-alpine
```


Setup `go` then add dependency `reflex`

```
go get github.com/cespare/reflex
```

### Start in docker

```
docker built -t director
docker run -p 127.0.0.1:10000:8080 director
```

### For dev purposes 

```
make watch
```

## API

