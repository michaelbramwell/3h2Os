FROM node:20-alpine

WORKDIR /app

# Copy package files first for better layer caching.
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy source code. The build context's .dockerignore excludes
# node_modules/, dist/, .env, and test artifacts so the host's
# versions do not leak into the image.
COPY index.html ./
COPY tsconfig*.json ./
COPY tsr.config.json ./
COPY vite.config.ts ./
COPY postcss.config.js ./
COPY tailwind.config.js ./
COPY public/ ./public/
COPY src/ ./src/

# Expose Vite port
EXPOSE 5173

# Start development server with host exposure
CMD ["npm", "run", "dev", "--", "--host"]
