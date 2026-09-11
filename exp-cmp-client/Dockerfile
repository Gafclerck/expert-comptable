FROM node:22-alpine

# pnpm (projet gere en pnpm : pnpm-lock.yaml, version pinee dans .mise.toml)
RUN corepack enable

WORKDIR /app

COPY package.json pnpm-lock.yaml ./

RUN pnpm install --frozen-lockfile

COPY . .

EXPOSE 5173

CMD ["pnpm", "run", "dev"]