# ─────────────────────────────────────────────────────────────────────────────
# Container for apps/web (Next.js) — built for Google Cloud Run.
# Multi-stage: install workspace deps -> build standalone -> minimal runtime.
# Build context is the repo root (apps/web is an npm workspace).
#
#   gcloud run deploy hapi-web --source . --region <region> \
#     --update-secrets DATABASE_URL=DATABASE_URL:latest --allow-unauthenticated
# ─────────────────────────────────────────────────────────────────────────────
FROM node:22-alpine AS deps
WORKDIR /app
# Install only what the workspaces need to resolve, for a cached dep layer.
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
COPY packages/contracts/package.json packages/contracts/package.json
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build --workspace apps/web

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
# Cloud Run sends traffic to $PORT (default 8080); Next standalone reads PORT/HOSTNAME.
ENV PORT=8080
ENV HOSTNAME=0.0.0.0
# Run as a non-root user.
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001

# Standalone output for a monorepo: server at apps/web/server.js + node_modules at root.
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/public ./apps/web/public

USER nextjs
EXPOSE 8080
CMD ["node", "apps/web/server.js"]
