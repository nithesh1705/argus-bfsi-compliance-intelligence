# ==============================================================================
# ARGUS — Frontend Multi-Stage Dockerfile (frontend/Dockerfile)
# ==============================================================================

# Build Stage
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# Runtime Stage with Nginx
FROM nginx:alpine AS runner

COPY --from=builder /app/dist /usr/share/nginx/html

ARG BACKEND_HOST="argus-backend-YOUR_PROJECT_NUMBER.asia-south1.run.app"

# Custom Nginx config supporting client-side routing and Cloud Run port 8080
RUN printf 'server {\n\
    listen 8080;\n\
    server_name localhost;\n\
    location /api/ {\n\
        proxy_pass https://%s/api/;\n\
        proxy_set_header Host %s;\n\
        proxy_ssl_server_name on;\n\
    }\n\
    location / {\n\
        root /usr/share/nginx/html;\n\
        index index.html index.htm;\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
}\n' "$BACKEND_HOST" "$BACKEND_HOST" > /etc/nginx/conf.d/default.conf

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
