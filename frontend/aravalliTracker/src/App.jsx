import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, ZoomControl, Marker, Popup } from 'react-leaflet';
import axios from 'axios';
import ReactMarkdown from 'react-markdown'; // Run: npm install react-markdown
import 'leaflet/dist/leaflet.css';

function App() {
  const [tileUrl, setTileUrl] = useState('');
  const [year, setYear] = useState(2024);
  const [hotspots, setHotspots] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedBrief, setSelectedBrief] = useState(null); // Stores {lat, lng, report}
  const [briefLoading, setBriefLoading] = useState(false);

  // 1. Fetch standard mining map on year change
  const fetchMap = async () => {
    try {
      const res = await axios.get(`http://localhost:5000/get_mining_map?year=${year}`);
      setTileUrl(res.data.tile_url);
    } catch (err) { console.error("Map Fetch Error", err); }
  };

  // 2. Run AI Cluster Analysis
  const runAI = async () => {
    setLoading(true);
    setHotspots([]);
    try {
      const res = await axios.get(`http://localhost:5000/get_ai_prediction`);
      if (res.data.tile_url) setTileUrl(res.data.tile_url);
      setHotspots(res.data.critical_points || []);
    } catch (err) { console.error("AI Analysis Error", err); }
    setLoading(false);
  };

  // 3. Fetch Gemini Scientific Briefing for a specific coordinate
  const fetchBriefing = async (lat, lng) => {
    setBriefLoading(true);
    setSelectedBrief({ lat, lng, report: "" }); // Open modal in loading state
    try {
      const res = await axios.get(`http://localhost:5000/get_gemini_report?lat=${lat}&lng=${lng}`);
      setSelectedBrief({ lat, lng, report: res.data.report });
    } catch (err) {
      console.error("Gemini Error", err);
      setSelectedBrief({ lat, lng, report: "Error generating report. Check Backend." });
    }
    setBriefLoading(false);
  };

  useEffect(() => { fetchMap(); }, [year]);

  // Handle Leaflet resize issues
  useEffect(() => {
    setTimeout(() => { window.dispatchEvent(new Event('resize')); }, 500);
  }, [tileUrl, hotspots]);

  return (
    <div style={styles.container}>
      {/* Navbar */}
      <nav style={styles.nav}>
        <div style={styles.logo}>
          <span style={{ color: '#4ade80' }}>⚡</span> ARAVALLI SENTINEL AI
        </div>
        <div style={styles.navControls}>
          <span style={{ fontSize: '14px', color: '#94a3b8' }}>Timeline: {year}</span>
          <input type="range" min="2016" max="2024" value={year} onChange={(e) => setYear(Number(e.target.value))} style={styles.slider} />
          <button onClick={runAI} style={styles.runBtn}>
            {loading ? '🛰️ ANALYZING...' : 'RUN CLUSTER ANALYSIS'}
          </button>
        </div>
      </nav>

      <div style={styles.mainContent}>
        {/* Sidebar */}
        <div style={styles.sidebar}>
          <h3 style={styles.sidebarTitle}>CRITICAL HOTSPOTS</h3>
          <div style={styles.listContainer}>
            {hotspots.length > 0 ? hotspots.map((pt, i) => (
              <div key={i} style={styles.coordCard}>
                <div style={styles.cardHeader}>
                  <b>ZONE {i + 1}</b>
                  <span style={styles.badge}>{pt.status}</span>
                </div>
                <p style={styles.coordText}>Lat: {pt.lat.toFixed(5)} | Lng: {pt.lng.toFixed(5)}</p>
                <button 
                  onClick={() => fetchBriefing(pt.lat, pt.lng)} 
                  style={styles.briefBtn}
                >
                  VIEW AI BRIEFING
                </button>
              </div>
            )) : (
              <div style={styles.emptyState}>Initialize Analysis to scan for illegal excavation signatures.</div>
            )}
          </div>
        </div>

        {/* Map View */}
        <div style={styles.mapArea}>
          {/* Scientific Legend */}
          <div style={styles.legend}>
            <div style={styles.legendHeader}>SPECTRAL INDEX</div>
            <div style={styles.legendItem}><div style={{...styles.dot, background: 'red'}}></div> Mining Scars</div>
            <div style={styles.legendItem}><div style={{...styles.dot, background: 'green'}}></div> Vegetative Cover</div>
            <div style={styles.legendItem}><div style={{...styles.dot, background: '#ff00ff'}}></div> AI Detected Cluster</div>
          </div>

          <MapContainer center={[28.3, 77.0]} zoom={10} style={{ height: '100%', width: '100%' }} zoomControl={false}>
            <ZoomControl position="bottomright" />
            <TileLayer 
              url="https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}" 
              subdomains={['mt0', 'mt1', 'mt2', 'mt3']} 
              attribution="Google Satellite"
            />
            {tileUrl && <TileLayer url={tileUrl} opacity={0.7} />}
            {hotspots.map((pt, i) => (
              <Marker key={i} position={[pt.lat, pt.lng]} />
            ))}
          </MapContainer>

          {/* AI Briefing Modal Overlay */}
          {selectedBrief && (
            <div style={styles.modalOverlay}>
              <div style={styles.modal}>
                <div style={styles.modalHeader}>
                  <h3>Enforcement Intelligence Report</h3>
                  <button onClick={() => setSelectedBrief(null)} style={styles.closeBtn}>&times;</button>
                </div>
                <div style={styles.modalBody}>
                  <p style={{ color: '#4ade80', marginBottom: '10px' }}>
                    Target: {selectedBrief.lat.toFixed(4)}, {selectedBrief.lng.toFixed(4)}
                  </p>
                  {briefLoading ? (
                    <div className="pulse">Consulting Gemini 2.0 Flash...</div>
                  ) : (
                    <div style={styles.reportContent}>
                      <ReactMarkdown>{selectedBrief.report}</ReactMarkdown>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <style>{`
        .pulse { animation: pulse 1.5s infinite; color: #4ade80; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
      `}</style>
    </div>
  );
}

const styles = {
  container: { height: '100vh', width: '100vw', display: 'flex', flexDirection: 'column', backgroundColor: '#020617', color: '#f8fafc', fontFamily: '"Inter", sans-serif' },
  nav: { height: '70px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 30px', background: '#0f172a', borderBottom: '1px solid #1e293b' },
  logo: { fontSize: '1.4rem', fontWeight: '800', letterSpacing: '1px' },
  navControls: { display: 'flex', alignItems: 'center', gap: '25px' },
  slider: { width: '150px', accentColor: '#4ade80' },
  runBtn: { padding: '10px 20px', backgroundColor: '#4ade80', color: '#020617', border: 'none', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer' },
  mainContent: { flex: 1, display: 'flex', overflow: 'hidden' },
  sidebar: { width: '320px', backgroundColor: '#0f172a', borderRight: '1px solid #1e293b', display: 'flex', flexDirection: 'column' },
  sidebarTitle: { padding: '20px', fontSize: '14px', letterSpacing: '1px', color: '#64748b', borderBottom: '1px solid #1e293b' },
  listContainer: { flex: 1, overflowY: 'auto', padding: '15px' },
  coordCard: { background: '#1e293b', padding: '15px', borderRadius: '10px', marginBottom: '15px', border: '1px solid #334155' },
  cardHeader: { display: 'flex', justifyContent: 'space-between', marginBottom: '8px' },
  badge: { fontSize: '9px', background: '#ef4444', color: 'white', padding: '2px 6px', borderRadius: '4px' },
  coordText: { fontSize: '12px', color: '#94a3b8', marginBottom: '12px' },
  briefBtn: { width: '100%', padding: '8px', background: 'transparent', border: '1px solid #4ade80', color: '#4ade80', borderRadius: '5px', fontSize: '11px', fontWeight: 'bold', cursor: 'pointer' },
  mapArea: { flex: 1, position: 'relative' },
  legend: { position: 'absolute', top: '20px', left: '20px', zIndex: 1000, background: 'rgba(15, 23, 42, 0.9)', padding: '15px', borderRadius: '8px', border: '1px solid #334155' },
  legendHeader: { fontSize: '10px', fontWeight: 'bold', color: '#64748b', marginBottom: '8px' },
  legendItem: { display: 'flex', alignItems: 'center', gap: '10px', fontSize: '12px', marginBottom: '5px' },
  dot: { width: '10px', height: '10px', borderRadius: '2px' },
  emptyState: { padding: '40px 20px', textAlign: 'center', color: '#475569', fontSize: '13px' },
  modalOverlay: { position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', background: 'rgba(2, 6, 23, 0.85)', zIndex: 2000, display: 'flex', justifyContent: 'center', alignItems: 'center' },
  modal: { width: '600px', maxHeight: '80%', background: '#0f172a', borderRadius: '12px', border: '1px solid #334155', display: 'flex', flexDirection: 'column' },
  modalHeader: { padding: '20px', borderBottom: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  closeBtn: { fontSize: '24px', background: 'none', border: 'none', color: '#64748b', cursor: 'pointer' },
  modalBody: { padding: '20px', overflowY: 'auto' },
  reportContent: { lineHeight: '1.6', fontSize: '14px', color: '#cbd5e1' }
};

export default App;