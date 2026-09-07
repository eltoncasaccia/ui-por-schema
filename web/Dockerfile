FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install

FROM node:20-alpine AS run
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
EXPOSE 5173
# Dev server de propósito: este projeto é para ser lido e mexido, não servido
# em produção. `docker compose up` dá recarga automática.
CMD ["npm", "run", "dev"]
