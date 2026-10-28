services:
  market-service:
    build:
      context: ./market_service
      dockerfile: Dockerfile
    container_name: portfolio-market
    ports:
      - "8003:8003"
    restart: unless-stopped