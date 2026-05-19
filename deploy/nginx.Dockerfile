# syntax=docker/dockerfile:1

FROM nginx:alpine

# Bake the config into the image so deploys via `docker compose pull && up -d`
# can update it without touching the host filesystem (which is owned by cloud-init).
COPY nginx.conf /etc/nginx/nginx.conf
