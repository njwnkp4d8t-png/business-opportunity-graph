# Business Opportunity Graph - Frontend

Modern React frontend for the Business Opportunity Knowledge Graph project. Built with Vite for fast development and optimized builds.

## Features

### Core Functionality
- **Dashboard** - Project overview with real-time statistics
- **Database Browser** - View and explore database tables
- **Documentation** - Access project docs and guides
- **Exports** - Browse and download CSV exports
- **Notebooks** - View Jupyter notebook status and info
- **Scripts** - SQL script documentation

### Modern UX Features
- 🎨 **Beautiful gradient animations** and smooth transitions
- 📱 **Fully responsive** design (mobile, tablet, desktop)
- 🌙 **Collapsible sidebar** for better screen real estate
- 🔄 **Loading states** with animated spinners
- ❌ **Error handling** with user-friendly messages and retry
- 🎯 **Icon-based navigation** for better visual recognition
- ✨ **Hover effects** and micro-interactions throughout

### Developer Features
- 🐛 **Debug Panel** - Real-time debugging information (dev mode only)
- 🔧 **Mock Data** - Work without a backend using realistic mock data
- 📊 **API Service Layer** - Clean separation of concerns
- 🛡️ **Error Boundaries** - Graceful error recovery
- 🔌 **Auto-Fallback** - Automatically falls back to mock data if API fails
- 📝 **ESLint** - Code quality and consistency
- 🎨 **Modern CSS** - No dependencies, pure CSS with animations

## Tech Stack

- **React 18** - UI framework
- **Vite 5** - Build tool and dev server
- **Axios** - HTTP client with interceptors
- **React Error Boundary** - Error handling
- **ESLint** - Code linting
- **Pure CSS** - No CSS frameworks, custom modern styling

## Project Structure

```
frontend/
├── public/                 # Static assets
├── src/
│   ├── components/        # React components
│   │   ├── ErrorBoundary.jsx
│   │   ├── LoadingSpinner.jsx
│   │   ├── ErrorMessage.jsx
│   │   └── DebugPanel.jsx
│   ├── hooks/            # Custom React hooks
│   │   └── useApi.js
│   ├── services/         # API and data services
│   │   ├── api.js
│   │   ├── dataService.js
│   │   └── mockData.js
│   ├── utils/            # Utility functions
│   │   └── debug.js
│   ├── config/           # Configuration
│   │   └── index.js
│   ├── App.jsx           # Main App component
│   ├── App.css           # Main styles
│   ├── index.css         # Global styles
│   └── main.jsx          # Entry point
├── .env.development      # Development environment variables
├── .env.example          # Example environment variables
├── .eslintrc.cjs         # ESLint configuration
├── index.html            # HTML template
├── package.json          # Dependencies
├── vite.config.js        # Vite configuration
└── README.md            # This file
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install
```

### Development

```bash
# Start development server (http://localhost:5173)
npm run dev

# Run with mock data enabled (no backend required)
# Edit .env.development and set VITE_ENABLE_MOCK_DATA=true
npm run dev
```

### Building

```bash
# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

## Environment Configuration

Create a `.env.development` file (or use the provided one):

```bash
# API Configuration
VITE_API_BASE_URL=http://localhost:8000
VITE_API_TIMEOUT=30000

# Feature Flags
VITE_ENABLE_DEBUG=true
VITE_ENABLE_MOCK_DATA=true  # Set to true to use mock data

# Application
VITE_APP_NAME=Business Opportunity Knowledge Graph
VITE_APP_VERSION=0.0.1
```

## Features Deep Dive

### API Service Layer

The app uses a layered architecture for data fetching:

```javascript
// services/api.js - Low-level HTTP client
import { api } from './services/api';
const { data, error } = await api.get('/api/tables');

// services/dataService.js - High-level data service
import dataService from './services/dataService';
const { data, error } = await dataService.getTables();
```

**Features:**
- Automatic request/response logging in debug mode
- Error handling with enhanced error objects
- Timeout configuration
- Automatic fallback to mock data

### Mock Data System

When `VITE_ENABLE_MOCK_DATA=true`, all API calls use mock data:

```javascript
// Realistic mock data with delays
export const mockApi = {
  getTables: async () => {
    await delay(500); // Simulate network latency
    return mockData.tables;
  },
};
```

**Benefits:**
- Work without a backend
- Consistent data for testing
- Realistic loading states
- Deterministic behavior

### Custom Hooks

#### useApi Hook

Simplifies data fetching with automatic state management:

```javascript
const { data, loading, error, refetch } = useApi(() => dataService.getTables());

if (loading) return <LoadingSpinner />;
if (error) return <ErrorMessage error={error} onRetry={refetch} />;
return <div>{data.map(...)}</div>;
```

**Features:**
- Automatic loading states
- Error handling
- Refetch capability
- Dependency tracking

### Debug Panel

Press the 🐛 button (bottom-right) to open the debug panel:

**Shows:**
- API configuration
- Mock data status
- Memory usage (if available)
- Viewport dimensions
- Environment info

**Actions:**
- Copy debug info to clipboard
- Clear console
- Reload page

### Error Handling

Multiple layers of error protection:

1. **Error Boundaries** - Catch React errors
2. **API Error Handling** - Network and HTTP errors
3. **Component Error States** - User-friendly error messages
4. **Automatic Retry** - One-click retry for failed requests

### Loading States

Beautiful loading indicators:
- Animated spinner with multiple rings
- Contextual loading messages
- Smooth transitions
- No layout shift

### Responsive Design

Breakpoints:
- **Desktop**: > 768px (full sidebar)
- **Tablet**: 480px - 768px (collapsible sidebar)
- **Mobile**: < 480px (compact layout)

## API Endpoints

The frontend expects these API endpoints (or uses mock data):

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/tables` | GET | Database tables list |
| `/api/exports` | GET | Export files list |
| `/api/notebooks` | GET | Jupyter notebooks list |
| `/api/scripts` | GET | SQL scripts list |
| `/api/stats` | GET | Dashboard statistics |
| `/health` | GET | Health check |

## Styling Guide

### Color Palette

```css
/* Primary Colors */
--blue: #2563eb
--indigo: #4f46e5
--pink: #ec4899
--green: #22c55e
--cyan: #06b6d4

/* Neutrals */
--slate-900: #1e293b
--slate-600: #475569
--slate-400: #94a3b8
--slate-200: #e2e8f0
--slate-50: #f8fafc
```

### Gradients

Each stat card uses a unique gradient:
```css
.stat-card:nth-child(1) { background: linear-gradient(135deg, #667eea, #764ba2); }
.stat-card:nth-child(2) { background: linear-gradient(135deg, #f093fb, #f5576c); }
/* ... */
```

### Animations

- `fadeIn` - Component entrance
- `slideIn` - Table row animation
- `spin` - Loading spinner
- `pulse` - Running status indicator
- `gradient-shift` - Top bar accent

## Development Tips

### Enable Debug Mode

Set `VITE_ENABLE_DEBUG=true` in `.env.development` to see:
- 🚀 API Request logs
- ✅ API Response logs
- ❌ API Error logs
- 📦 Mock data usage
- ℹ️ Navigation changes

### Hot Module Replacement (HMR)

Vite provides instant updates without page reload:
- Edit CSS - instant visual update
- Edit JSX - preserves component state
- Edit config - full reload

### Code Linting

```bash
# Run ESLint
npm run lint

# Auto-fix issues
npm run lint -- --fix
```

### Performance Optimization

- Code splitting (React vendor chunk)
- Lazy loading (React.lazy) ready
- Image optimization
- CSS animations (GPU-accelerated)
- Minimal re-renders

## Debugging

### Common Issues

**Port 5173 already in use:**
```bash
# Kill existing process or change port in vite.config.js
```

**API connection errors:**
```bash
# Enable mock data in .env.development
VITE_ENABLE_MOCK_DATA=true
```

**ESLint errors:**
```bash
# Auto-fix
npm run lint -- --fix
```

### Browser DevTools

1. Open React DevTools extension
2. Check Console for debug logs (if debug mode enabled)
3. Network tab shows API calls
4. Components tab shows React hierarchy

## Deployment

### Build for Production

```bash
npm run build
# Output: dist/
```

### Serve Static Files

The build output (`dist/`) can be served by:
- Nginx (configured in docker/nginx.conf)
- Apache
- Any static file server

### Environment Variables

Set production environment variables:
```bash
VITE_API_BASE_URL=https://api.yourdomain.com
VITE_ENABLE_DEBUG=false
VITE_ENABLE_MOCK_DATA=false
```

## Contributing

### Code Style

- Use functional components
- Prefer hooks over class components
- Keep components focused and small
- Use destructuring for props
- Add JSDoc comments for functions

### Naming Conventions

- **Components**: PascalCase (e.g., `LoadingSpinner`)
- **Files**: camelCase for utilities, PascalCase for components
- **CSS Classes**: kebab-case (e.g., `stat-card`)
- **Constants**: SCREAMING_SNAKE_CASE

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature

# Make changes, commit
git commit -m "Add feature X"

# Push and create PR
git push origin feature/your-feature
```

## Future Enhancements

Potential improvements:
- [ ] Dark mode toggle
- [ ] Data visualization with charts
- [ ] Real-time WebSocket updates
- [ ] Advanced filtering and search
- [ ] Data export functionality
- [ ] User preferences persistence
- [ ] Internationalization (i18n)
- [ ] Accessibility improvements (ARIA labels)

## License

Part of the UCSD DSE 203 class project.

## Support

For issues or questions:
1. Check this README
2. Review [docker/README.md](../docker/README.md)
3. Check browser console for errors
4. Enable debug panel for diagnostics
