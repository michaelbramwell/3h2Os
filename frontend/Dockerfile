FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Expose Vite port
EXPOSE 5173

# Start development server with host exposure
CMD ["npm", "run", "dev", "--", "--host"]
