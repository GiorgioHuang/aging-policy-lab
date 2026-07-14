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
# Canonical public origin for SEO (canonical URLs, Open Graph, sitemap, JSON-LD).
# NEXT_PUBLIC_* is inlined at build time, so pass it here to bake the real domain
# into static pages:  gcloud builds ... --substitutions ... / docker build --build-arg
# NEXT_PUBLIC_SITE_URL=https://your-domain.ca . A safe placeholder is used if unset.
ARG NEXT_PUBLIC_SITE_URL
ENV NEXT_PUBLIC_SITE_URL=${NEXT_PUBLIC_SITE_URL}
# Deployed build id shown in the footer. Pass the commit SHA to bake the exact
# version:  docker build --build-arg NEXT_PUBLIC_APP_VERSION=$SHORT_SHA . (falls
# back to the committed short SHA in apps/web/lib/version.ts when unset).
ARG NEXT_PUBLIC_APP_VERSION
ENV NEXT_PUBLIC_APP_VERSION=${NEXT_PUBLIC_APP_VERSION}
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
