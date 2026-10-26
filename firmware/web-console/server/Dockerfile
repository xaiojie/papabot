# 爬爬 · WebSocket 中转服务
FROM node:20-alpine

WORKDIR /app

# 先装依赖（利用 Docker 层缓存）
COPY package.json ./
RUN npm install --omit=dev --no-audit --no-fund

# 再复制源码
COPY server.js ./

# 交给非 root 用户（COPY 默认属主是 root，不 chown 的话 node 用户读不了）
RUN chown -R node:node /app

USER node

EXPOSE 8790

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:8790/api/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "server.js"]
