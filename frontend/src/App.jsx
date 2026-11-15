import Saved from './pages/Saved';
import Information from './pages/Information';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import TopNav from './components/TopNav';
import Home from './pages/Home';
import Results from './pages/Results';
import ProductDetail from './pages/ProductDetail';
import Onboarding from './pages/Onboarding';
import ScraperDashboard from './components/ScraperDashboard';

export default function App() {
  return (
    <Router>
      <div className="min-h-screen bg-lighter font-sans text-text flex flex-col">
        <TopNav />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/results" element={<Results />} />
          <Route path="/product/:id" element={<ProductDetail />} />
          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="/saved" element={<Saved />} />
          {['about', 'privacy', 'terms', 'contact'].map(page => <Route key={page} path={`/${page}`} element={<Information page={page} />} />)}
          <Route path="/admin" element={<ScraperDashboard />} />
          <Route path="*" element={<Home />} />
        </Routes>
      </div>
    </Router>
  );
}
