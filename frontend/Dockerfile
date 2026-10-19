# Dev image: runs the Vite dev server with hot reload.
# docker-compose bind-mounts ./frontend over /app, and keeps node_modules in an
# anonymous volume so the container's Linux install isn't overwritten by the host's.
FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev"]
