#!/bin/bash

# Backend Deployment
cd geopolitical-data-platform
git init
git add .
git commit -m "Initial commit: Geo-political Data Platform Backend"
git remote add origin https://github.com/jamaican999/geopolitical-data-platform-backend.git
git push -u origin main
cd ..

# Frontend Deployment
cd geopolitical-frontend
git init
git add .
git commit -m "Initial commit: Geo-political Data Platform Frontend"
git remote add origin https://github.com/jamaican999/geopolitical-data-platform-frontend.git
git push -u origin main
cd ..

echo "✅ Code pushed to two separate GitHub repositories."
echo "Next: Deploy Backend to Render (Phase 3 )"

