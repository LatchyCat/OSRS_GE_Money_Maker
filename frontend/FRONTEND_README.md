# OSRS High Alch Tracker - Frontend

A beautiful, modern React frontend for the OSRS High Alch Item Recommender system with glassmorphism design.

## 🚀 Features

- **Glassmorphism Design**: Beautiful glass-like UI components with backdrop blur effects
- **Real-time Data**: Live connection to Django backend API
- **Responsive Design**: Mobile-first approach with Tailwind CSS
- **Item Tracking**: Browse and filter 4,307+ OSRS items
- **Market Analysis**: View real-time market statistics and trends
- **Search & Filters**: Advanced filtering and search capabilities
- **Goal Planning**: (Coming soon) Create and track wealth-building goals
- **AI Recommendations**: (Coming soon) AI-powered profit suggestions

## 🛠️ Tech Stack

- **React 19** with TypeScript
- **Vite** for fast development and building
- **Tailwind CSS** with custom glassmorphism design
- **Framer Motion** for smooth animations
- **Axios** for API communication
- **React Router** for navigation
- **Lucide React** for beautiful icons

## 🎨 Design System

### Color Palette
- **Primary**: Deep blue/purple gradients (`#0F172A` to `#1E1B4B`)
- **Accent**: Gold/yellow (`#F59E0B`, `#EAB308`)
- **Glass Effect**: `backdrop-blur-md bg-white/10 border border-white/20`

### Components
- Glassmorphism cards and overlays
- Animated buttons with hover effects
- Gradient text and backgrounds
- Responsive navigation with mobile sidebar

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ or Bun
- OSRS High Alch Tracker backend running on port 8080

### Installation

```bash
# Install dependencies
bun install

# Start development server
bun run dev
```

The frontend will be available at `http://localhost:5173`

### Backend Integration

The frontend expects the Django backend to be running on `http://localhost:8080`. 

Key API endpoints used:
- `GET /api/v1/items/` - Item catalog with profit data
- `GET /api/v1/planning/market-analysis/` - Market statistics
- `GET /api/v1/planning/stats/` - Goal plan statistics

## 📁 Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── layout/         # Navigation and layout components
│   ├── ui/            # Base UI components (Button, Card, etc.)
│   └── features/      # Feature-specific components
├── views/              # Page components (Dashboard, Items, etc.)
├── api/               # API client and service functions
├── types/             # TypeScript type definitions
└── styles/            # Global styles and Tailwind config
```

## 🎯 Views

### Dashboard (`/`)
- Market overview with key statistics
- Top profitable items grid
- Quick access to main features

### Items (`/items`)
- Complete item catalog with search and filters
- Grid and list view modes
- Profit calculations and recommendations

### Coming Soon
- **Recommendations** (`/recommendations`) - AI-powered suggestions
- **Goal Planning** (`/planning`) - Create and track goals
- **Analytics** (`/analytics`) - Advanced market insights

## 🔧 Development

### Available Scripts
- `bun run dev` - Start development server
- `bun run build` - Build for production  
- `bun run preview` - Preview production build
- `bun run lint` - Run ESLint

### API Integration

The app uses Axios with automatic cookie-based session management:

```typescript
// API client with base configuration
const apiClient = axios.create({
  baseURL: 'http://localhost:8080/api/v1',
  withCredentials: true, // For Django sessions
});
```

### Styling

Custom Tailwind classes for glassmorphism:
- `.glass` - Basic glass effect
- `.glass-hover` - Interactive glass with hover
- `.glass-card` - Pre-styled glass card
- `.btn-primary` - Gradient primary button
- `.text-gradient` - Gradient text effect

## 🌟 Key Features Implemented

✅ **Complete UI Framework** - All core components built  
✅ **Backend Integration** - Full API connectivity  
✅ **Glassmorphism Theme** - Beautiful modern design  
✅ **Responsive Design** - Mobile and desktop support  
✅ **Item Catalog** - Browse 4,307 OSRS items  
✅ **Market Data** - Real-time profit calculations  
✅ **Search & Filters** - Advanced item filtering  
✅ **Navigation** - Router-based multi-page app  

🚧 **Coming Soon** - Goal planning, AI recommendations, advanced analytics

## 📱 Screenshots

The app features a beautiful glassmorphism design with:
- Translucent cards with backdrop blur
- Gradient accents and gold highlights  
- Smooth animations and transitions
- Dark theme with excellent contrast
- Mobile-responsive navigation

---

Built with ❤️ for the OSRS community