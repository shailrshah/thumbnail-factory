FROM public.ecr.aws/docker/library/node:24-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci


# Vite dev server with HMR; used by compose.override.yml.
FROM deps AS dev
COPY . .
EXPOSE 5173
CMD ["npx", "vite", "--host", "0.0.0.0"]


FROM deps AS build
COPY . .
RUN npm run build


# Last stage, so it's what a plain `docker build` produces.
FROM public.ecr.aws/nginx/nginx-unprivileged:alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
