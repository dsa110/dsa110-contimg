# Playwright E2E Test Runner
# Uses official Playwright Docker image with all browsers pre-installed

FROM mcr.microsoft.com/playwright:v1.49.0-noble

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy test files and config
COPY playwright.config.ts ./
COPY e2e/ ./e2e/
COPY src/ ./src/
COPY tsconfig.json ./
COPY tsconfig.test.json ./
COPY vite.config.ts ./
COPY index.html ./

# Set environment
ENV CI=true

# Default command runs all E2E tests
CMD ["npx", "playwright", "test", "--reporter=html"]
