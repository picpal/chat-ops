# ChatOps UI

React-based frontend for the ChatOps AI Backoffice system.

## Tech Stack

- **React 18** with TypeScript
- **Vite** for build tooling
- **Tailwind CSS** for styling
- **Zustand** for state management
- **TanStack Query** (React Query) for data fetching
- **Recharts** for data visualization
- **React Markdown** for content rendering

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend services running:
  - AI Orchestrator on `http://localhost:8000`
  - Core API on `http://localhost:8080`

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at `http://localhost:3000`

### Alternative: Use the development script

```bash
# From project root
./scripts/dev-ui.sh
```

## Project Structure

```
src/
├── api/              # API clients (axios)
├── assets/           # Static assets
├── components/       # React components
│   ├── chat/         # Chat interface components
│   ├── common/       # Reusable UI components
│   ├── layout/       # Layout components (Sidebar, Header, etc.)
│   ├── modals/       # Modal dialogs
│   └── renderers/    # RenderSpec renderers (Table, Chart, etc.)
├── hooks/            # Custom React hooks
├── store/            # Zustand stores
├── styles/           # Global styles
├── types/            # TypeScript type definitions
└── utils/            # Utility functions
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript type checking

## Environment Variables

Create a `.env` file in the root directory:

```env
VITE_AI_API_URL=http://localhost:8000
VITE_CORE_API_URL=http://localhost:8080
VITE_APP_NAME=ChatOps AI Backoffice
VITE_APP_VERSION=2.4
```

## Features

### Current Implementation

- ✅ Sidebar navigation with session history
- ✅ Chat interface with real-time messaging
- ✅ New Analysis modal for creating sessions
- ✅ State management with Zustand
- ✅ API integration with AI Orchestrator and Core API
- ✅ TypeScript type safety
- ✅ Responsive design with Tailwind CSS

### Coming Soon

- 🔄 RenderSpec renderers (Table, Text, Chart, Log)
- 🔄 Pagination with queryToken
- 🔄 Advanced modals (Table Detail, Chart Detail, Log Detail)
- 🔄 Export functionality (CSV, PDF)
- 🔄 Search and filtering

## Design System

### Colors

- Primary: `#137fec`
- Success: `emerald-500/600/700`
- Error: `red-500/600/700`
- Warning: `amber-500/600/700`
- Neutral: `slate-50 to slate-900`

### Typography

- Font: Inter (400, 500, 700, 900 weights)
- Icons: Material Symbols Outlined

## Development Notes

- The app uses Vite proxy to forward API requests to backend services
- All API calls go through centralized axios clients with error handling
- State is managed with Zustand for simplicity and performance
- TanStack Query handles caching and synchronization with the server

## Troubleshooting

### CORS Issues

If you encounter CORS errors, ensure the backend services are configured to accept requests from `http://localhost:3000`, or use the Vite proxy configuration (already set up in `vite.config.ts`).

### API Connection Issues

1. Verify backend services are running:
   - AI Orchestrator: `http://localhost:8000/health`
   - Core API: `http://localhost:8080/api/v1/query/health`

2. Check environment variables in `.env` file

### Build Issues

If you encounter build errors:

```bash
# Clean install
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf node_modules/.vite
npm run dev
```

## Contributing

1. Follow existing code structure and naming conventions
2. Use TypeScript for type safety
3. Write clean, self-documenting code
4. Test components before committing

## License

Private project - All rights reserved
