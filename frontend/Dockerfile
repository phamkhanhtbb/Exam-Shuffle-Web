# Stage 1: Build
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies using npm
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Build args for production API URL (Vite requires VITE_ prefix)
ARG VITE_API_URL=https://api.trondeonline.me

ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Copy built files (Vite outputs to 'build' as configured in vite.config.ts)
COPY --from=build /app/build /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
