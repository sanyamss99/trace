# ---- Build stage ----
FROM node:20-alpine AS build

WORKDIR /app

ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Install dependencies first for layer caching
COPY package.json package-lock.json* ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# ---- Runtime stage ----
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf.template

# Default values for docker-compose; override on Railway
ENV API_URL=http://api:8000
ENV PORT=80

EXPOSE 80

# Only substitute $API_URL and $PORT, leaving nginx variables ($host, $uri, etc.) intact
CMD ["/bin/sh", "-c", "envsubst '$API_URL $PORT' < /etc/nginx/nginx.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
