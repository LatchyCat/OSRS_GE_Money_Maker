import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { Dashboard } from './views/Dashboard';
import { Items } from './views/Items';
import { ItemDetail } from './views/ItemDetail';
import { Planning } from './views/Planning';
import { PlanDetail } from './views/PlanDetail';
import { CreatePlan } from './views/CreatePlan';
import { Analytics } from './views/Analytics';
import { AIRecommendations } from './views/AIRecommendations';
import { TradingStrategies } from './views/TradingStrategies';
import { HighAlchemyView } from './views/HighAlchemyView';
import { DecantingView } from './views/DecantingView';
import { FlippingView } from './views/FlippingView';
import { CraftingView } from './views/CraftingView';
import { MagicRunesView } from './views/MagicRunesView';
import { SetCombiningView } from './views/SetCombiningView';
import { SeasonalAnalyticsView } from './components/seasonal/SeasonalAnalyticsView';
import { SeasonalDataProvider } from './contexts/SeasonalDataContext';
import { ReactiveTradingProvider } from './contexts/ReactiveTrading';
import { MoneyMakerDashboard } from './views/MoneyMakerDashboard';



const NotFound: React.FC = () => (
  <div className="text-center py-12">
    <h1 className="text-3xl font-bold text-white mb-4">404 - Not Found</h1>
    <p className="text-gray-400">The page you're looking for doesn't exist.</p>
  </div>
);

function App() {
  return (
    <SeasonalDataProvider>
      <ReactiveTradingProvider>
        <Router>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route path="high-alchemy" element={<HighAlchemyView />} />
              <Route path="decanting" element={<DecantingView />} />
              <Route path="flipping" element={<FlippingView />} />
              <Route path="crafting" element={<CraftingView />} />
              <Route path="magic-runes" element={<MagicRunesView />} />
              <Route path="set-combining" element={<SetCombiningView />} />
              <Route path="items" element={<Items />} />
              <Route path="items/:id" element={<ItemDetail />} />
              <Route path="recommendations" element={<AIRecommendations />} />
              <Route path="planning" element={<Planning />} />
              <Route path="planning/create" element={<CreatePlan />} />
              <Route path="planning/:planId" element={<PlanDetail />} />
              <Route path="analytics" element={<Analytics />} />
              <Route path="trading-strategies" element={<TradingStrategies />} />
              <Route path="money-makers" element={<MoneyMakerDashboard />} />
              <Route path="seasonal-dashboard" element={<SeasonalAnalyticsView />} />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </Router>
      </ReactiveTradingProvider>
    </SeasonalDataProvider>
  );
}

export default App;
