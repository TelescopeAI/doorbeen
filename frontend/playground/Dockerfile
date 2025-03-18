# Build stage
FROM node:22-alpine AS build

RUN corepack enable

WORKDIR /app

# Add build dependencies
RUN apk add --no-cache python3 make g++ sqlite-dev

# Define build args for all environment variables
ARG NODE_ENV
ARG VITE_API_SERVER_URL
ARG API_SERVER_URL
ARG NUXT_PUBLIC_API_SERVER_URL
ARG FORMKIT_PRO_LICENSE_KEY
ARG GOOGLE_OAUTH_CLIENT_ID
ARG GOOGLE_OAUTH_CLIENT_SECRET
ARG AUTH_SECRET
ARG CLERK_PUBLIC_KEY
ARG NUXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ARG CLERK_SECRET_KEY
ARG NUXT_CLERK_SECRET_KEY
ARG CLERK_DOMAIN
ARG ALLOWED_DOMAINS
ARG GTAG_ID
ARG POSTGRES_USER
ARG POSTGRES_PASSWORD
ARG POSTGRES_DB

# Copy package.json and yarn.lock
COPY package*.json yarn.lock* ./

# Install dependencies
RUN yarn install

# Copy the rest of the code
COPY . .

# Create .env file with all environment variables
RUN touch .env && \
    [ ! -z "$NODE_ENV" ] && echo "NODE_ENV=${NODE_ENV}" >> .env || true && \
    [ ! -z "$VITE_API_SERVER_URL" ] && echo "VITE_API_SERVER_URL=${VITE_API_SERVER_URL}" >> .env || true && \
    [ ! -z "$API_SERVER_URL" ] && echo "API_SERVER_URL=${API_SERVER_URL}" >> .env || true && \
    [ ! -z "$NUXT_PUBLIC_API_SERVER_URL" ] && echo "NUXT_PUBLIC_API_SERVER_URL=${NUXT_PUBLIC_API_SERVER_URL}" >> .env || true && \
    [ ! -z "$FORMKIT_PRO_LICENSE_KEY" ] && echo "FORMKIT_PRO_LICENSE_KEY=${FORMKIT_PRO_LICENSE_KEY}" >> .env || true && \
    [ ! -z "$GOOGLE_OAUTH_CLIENT_ID" ] && echo "GOOGLE_OAUTH_CLIENT_ID=${GOOGLE_OAUTH_CLIENT_ID}" >> .env || true && \
    [ ! -z "$GOOGLE_OAUTH_CLIENT_SECRET" ] && echo "GOOGLE_OAUTH_CLIENT_SECRET=${GOOGLE_OAUTH_CLIENT_SECRET}" >> .env || true && \
    [ ! -z "$AUTH_SECRET" ] && echo "AUTH_SECRET=${AUTH_SECRET}" >> .env || true && \
    [ ! -z "$CLERK_PUBLIC_KEY" ] && echo "CLERK_PUBLIC_KEY=${CLERK_PUBLIC_KEY}" >> .env || true && \
    [ ! -z "$NUXT_PUBLIC_CLERK_PUBLISHABLE_KEY" ] && echo "NUXT_PUBLIC_CLERK_PUBLISHABLE_KEY=${NUXT_PUBLIC_CLERK_PUBLISHABLE_KEY}" >> .env || true && \
    [ ! -z "$CLERK_SECRET_KEY" ] && echo "CLERK_SECRET_KEY=${CLERK_SECRET_KEY}" >> .env || true && \
    [ ! -z "$NUXT_CLERK_SECRET_KEY" ] && echo "NUXT_CLERK_SECRET_KEY=${NUXT_CLERK_SECRET_KEY}" >> .env || true && \
    [ ! -z "$CLERK_DOMAIN" ] && echo "CLERK_DOMAIN=${CLERK_DOMAIN}" >> .env || true && \
    [ ! -z "$ALLOWED_DOMAINS" ] && echo "ALLOWED_DOMAINS=${ALLOWED_DOMAINS}" >> .env || true && \
    [ ! -z "$GTAG_ID" ] && echo "GTAG_ID=${GTAG_ID}" >> .env || true && \
    [ ! -z "$POSTGRES_USER" ] && echo "POSTGRES_USER=${POSTGRES_USER}" >> .env || true && \
    [ ! -z "$POSTGRES_PASSWORD" ] && echo "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}" >> .env || true && \
    [ ! -z "$POSTGRES_DB" ] && echo "POSTGRES_DB=${POSTGRES_DB}" >> .env || true

# Generate static files
RUN yarn generate || (echo "Build failed. See error above." && exit 1)

# Serving stage
FROM node:22-alpine AS serve

WORKDIR /app

# Install serve globally
RUN yarn global add serve

# Copy built assets from the build stage
COPY --from=build /app/.output/public ./public

# Expose port
EXPOSE 3000

# Start the static server
CMD ["serve", "-s", "public", "-l", "3000"]