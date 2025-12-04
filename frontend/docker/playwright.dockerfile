# Playwright E2E Test Runner
# Uses official Playwright Docker image with all browsers pre-installed

FROM mcr.microsoft.com/playwright:v1.49.0-noble

WORKDIR /app

# Copy package files and vendor dependencies first
COPY package*.json ./
COPY vendor/ ./vendor/

# Install dependencies
RUN npm ci

# Copy ALL source files for frontend dev server
COPY . .

# Set environment
ENV CI=true

# Default command runs all E2E tests
CMD ["npx", "playwright", "test", "--reporter=html"]
