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
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Only substitute API_URL, leave nginx variables ($uri, $host, etc.) untouched
ENV NGINX_ENVSUBST_OUTPUT_DIR=/etc/nginx/conf.d
ENV NGINX_ENVSUBST_FILTER=API_URL|PORT

# Default values for docker-compose; override on Railway
ENV API_URL=http://api:8000
ENV PORT=80

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
