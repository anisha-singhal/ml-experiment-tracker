# syntax=docker/dockerfile:1

# ---------- stage 1: build the bundle ----------
FROM node:20-alpine AS build

WORKDIR /app

# package.json alone first: dependencies only reinstall when they actually change.
COPY package.json ./
RUN npm install

COPY . .
RUN npm run build

# ---------- stage 2: serve it ----------
# nginx-unprivileged rather than plain nginx: it already runs as uid 101 and
# listens on 8080, so no capability is needed to bind the port and no
# chown/chmod gymnastics are needed to let a non-root user write its pid file.
FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime

# Only the built assets cross the stage boundary. node_modules, the Vite
# toolchain and the source never reach the final image.
COPY --from=build /app/dist /usr/share/nginx/html

# The base image's entrypoint renders every *.template through envsubst.
# NGINX_ENVSUBST_FILTER restricts that to BACKEND_URL, so nginx's own
# variables ($host, $remote_addr, ...) survive untouched.
COPY nginx.conf /etc/nginx/templates/default.conf.template
ENV NGINX_ENVSUBST_FILTER=BACKEND_URL \
    BACKEND_URL=http://backend:8000

USER 101

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1
