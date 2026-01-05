#!/bin/bash

# Navigate to UI directory
cd "$(dirname "$0")/../services/ui" || exit 1

echo "🚀 Starting ChatOps UI development server..."
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo ""
fi

# Start development server
echo "✨ Launching Vite dev server on http://localhost:3000"
echo ""
npm run dev
