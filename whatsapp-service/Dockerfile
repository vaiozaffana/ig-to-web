FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install --omit=dev

# Copy source
COPY src ./src

# Auth info akan di-mount sebagai volume
VOLUME /app/auth_info_baileys

EXPOSE 3001

CMD ["npm", "start"]
