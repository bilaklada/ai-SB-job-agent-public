# Frontend Dockerfile for AI Job Agent
# Multi-stage build for optimized production image

# Stage 1: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci


# Stage 2: Builder
FROM node:20-alpine AS builder
WORKDIR /app

# Accept backend URL at build time (used by next.config.ts during next build)
ARG BACKEND_URL
ENV BACKEND_URL=$BACKEND_URL

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy source code
COPY . .

# Build Next.js app
RUN npm run build


# Stage 3: Runner (Production)
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

# Accept backend URL at runtime as well (safe to keep consistent)
ARG BACKEND_URL
ENV BACKEND_URL=$BACKEND_URL

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy built app from builder
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Set ownership
RUN chown -R nextjs:nodejs /app

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
