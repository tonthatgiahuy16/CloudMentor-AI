FROM golang:1.24.8-alpine3.21 AS build

ARG MINIO_REF=RELEASE.2025-10-15T17-29-55Z

RUN apk add --no-cache git
RUN git clone --depth 1 --branch "${MINIO_REF}" \
    https://github.com/minio/minio.git /src

WORKDIR /src

RUN CGO_ENABLED=0 go build -trimpath -o /out/minio .

FROM alpine:3.21

COPY --from=build /out/minio /usr/local/bin/minio

EXPOSE 9000

ENTRYPOINT ["minio"]
CMD ["server", "/data", "--address", ":9000"]
