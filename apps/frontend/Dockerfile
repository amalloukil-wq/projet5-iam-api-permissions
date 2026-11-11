# Application Angular : construction (Node) puis service des fichiers statiques (nginx)
FROM node:22 AS build
WORKDIR /app
COPY app/package*.json ./
RUN npm ci
COPY app/ ./
RUN npx ng build \
 && mkdir -p /out \
 && (cp -r dist/app/browser/. /out/ 2>/dev/null || cp -r dist/app/. /out/)

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /out /usr/share/nginx/html
EXPOSE 80
