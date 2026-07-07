# ==============================================================
# FIN-SYS OS — Frontend Dockerfile
# Vite build → Nginx (solo frontend estático)
# ==============================================================

# --- Stage 1: Build ---
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
# npm install (no ci): el lockfile generado en Windows omite optionalDeps de linux
RUN npm install --no-audit --no-fund
COPY . .
RUN npm run build

# --- Stage 2: Serve ---
FROM nginx:alpine

# Copiar build a Nginx
COPY --from=build /app/dist /usr/share/nginx/html

# Configuración de Nginx para SPA + proxy al backend
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
