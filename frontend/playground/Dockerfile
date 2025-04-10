# Build stage
FROM node:22-alpine AS build
WORKDIR /app
RUN corepack enable
RUN corepack use yarn@latest

# Add build dependencies
RUN apk add --no-cache python3 make g++ sqlite-dev

# Define build args for all environment variables
ARG NODE_ENV
ARG API_SERVER_URL
ARG FORMKIT_PRO_LICENSE_KEY
ARG NUXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ARG NUXT_CLERK_SECRET_KEY
ARG CLERK_DOMAIN
ARG ALLOWED_DOMAINS
ARG GTAG_ID

# Copy package.json and yarn.lock
COPY package*.json yarn.lock* ./

# Install dependencies
RUN yarn install

# Copy the rest of the code
COPY . .

# Copy the local.env file and rename it to .env
COPY ./local.env /app/.env

# Load environment variables from .env file
ENV $(cat .env | xargs)

# Print .env file contents for debugging
RUN echo "==== .env file contents ====" && cat .env

# Generate static files
RUN yarn generate || (echo "Build failed. See error above." && exit 1)

# Serving stage
FROM node:22-alpine AS serve

WORKDIR /app
RUN corepack enable

# Install serve using npm instead of yarn global
RUN npm install -g serve

# Copy built assets from the build stage
COPY --from=build /app/.output/public ./public

# Expose port
EXPOSE 3000

# Start the static server
CMD ["serve", "-s", "public", "-l", "3000"]