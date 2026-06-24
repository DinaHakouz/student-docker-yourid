# Student Data Management System

A three-container Dockerized student information management app with MySQL, Flask, and Nginx.

## Overview

This project provides a browser-based CRUD system for students, courses, and enrollments. The stack includes:
- `nginx` as a reverse proxy
- `app` container running a Flask web application
- `db` container running MySQL 8

## Architecture

Browser → Nginx:80 → App:5000 → MySQL:3306

## Prerequisites

- Docker Engine 24+
- Docker Compose v2

## Run Locally (from source)

1. Copy the example env file:
   ```powershell
   cp env.example .env
   ```
2. Edit `.env` with secure credentials.
3. Start the stack:
   ```powershell
   docker compose up --build
   ```
4. Open `http://localhost`

## Run from Docker Hub

Pull a published image and use the compose stack with the same configuration. Example:

```powershell
docker pull yourdockerhubusername/student-app:latest
```

Update `docker-compose.yml` to use the pulled image for the `app` service, then run:

```powershell
docker compose up
```

## Environment Variables

See `env.example` for full variable names.

Required:
- `DB_ROOT_PASSWORD`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
