# Zyrox API

A Flask-based API for automating TikTok views using Zefoy.com

## 🚀 Features

- Send views to TikTok videos
- Check service status
- Web interface for easy testing
- RESTful API endpoints
- Docker support for easy deployment
- Optimized for Render.com

## 📡 API Endpoints

### GET `/`
Web interface for testing

### GET `/health`
Health check endpoint

### GET `/api/status`
Check which services are online

**Response:**
```json
{
  "success": true,
  "services": {
    "views": "online",
    "followers": "offline",
    "hearts": "online"
  }
}
