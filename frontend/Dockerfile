# Dockerfile do front-end — SGI-YKR (Angular build + Nginx)
# Multi-stage: (1) compila o Angular; (2) serve o estático com Nginx.

# --- Stage 1: build ---------------------------------------------------------
FROM node:20-alpine AS build
WORKDIR /app

# Instala dependências primeiro (camada cacheável).
COPY package.json package-lock.json ./
RUN npm ci

# Copia o restante e gera o build de produção.
COPY . .
RUN npm run build

# --- Stage 2: runtime (Nginx) ----------------------------------------------
FROM nginx:1.27-alpine

# Configuração do Nginx (SPA fallback + proxy /api).
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copia o build gerado no stage anterior. O builder :application do Angular 17
# emite os artefatos servíveis em dist/ynk-app/browser.
COPY --from=build /app/dist/ynk-app/browser /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q --spider http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
