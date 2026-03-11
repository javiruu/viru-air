FROM node:22-slim

WORKDIR /app

COPY frontend/package.json /app/package.json
COPY frontend/package-lock.json /app/package-lock.json

RUN npm ci

COPY frontend /app

RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start"]
