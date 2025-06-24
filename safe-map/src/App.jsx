import { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import ReactMarkdown from 'react-markdown';

function stripThinking(text) {
  return text.replace(/<think>[\s\S]*?<\/think>/gi, '').trim();
}

function App() {
  const mapRef = useRef(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [newsData, setNewsData] = useState([]);
  const [summary, setSummary] = useState({});
  const [loading, setLoading] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatTitle, setChatTitle] = useState('');
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);


  const mapTilerKey = import.meta.env.VITE_MAPTILER_KEY;

  useEffect(() => {
    const map = new maplibregl.Map({
      container: mapRef.current,
      style: {
        version: 8,
        glyphs: `https://api.maptiler.com/fonts/{fontstack}/{range}.pbf?key=${mapTilerKey}`,
        sources: {
          openmaptiles: {
            type: 'vector',
            url: `https://api.maptiler.com/tiles/v3/tiles.json?key=${mapTilerKey}`
          }
        },
        layers: [
          {
            id: 'background',
            type: 'background',
            paint: {
              'background-color': '#000000'
            }
          },
          {
            id: 'borders-all',
            type: 'line',
            source: 'openmaptiles',
            'source-layer': 'boundary',
            filter: ['all', ['==', '$type', 'LineString']],
            paint: {
              'line-color': '#00FF88',
              'line-width': [
                'match',
                ['get', 'admin_level'],
                2, 2.0,
                4, 1.5,
                6, 1.0,
                8, 0.6,
                0.5
              ],
              'line-opacity': 0.85
            }
          },
          {
            id: 'label-country',
            type: 'symbol',
            source: 'openmaptiles',
            'source-layer': 'place',
            filter: ['==', 'class', 'country'],
            layout: {
              'text-field': ['get', 'name:en'],
              'text-size': 14,
              'text-transform': 'uppercase'
            },
            paint: {
              'text-color': '#00FF88',
              'text-halo-color': '#000000',
              'text-halo-width': 1.2
            }
          },
          {
            id: 'label-state',
            type: 'symbol',
            source: 'openmaptiles',
            'source-layer': 'place',
            filter: ['==', 'class', 'state'],
            layout: {
              'text-field': ['get', 'name:en'],
              'text-size': 12
            },
            paint: {
              'text-color': '#00FF88',
              'text-halo-color': '#000000',
              'text-halo-width': 1.2
            }
          },
          {
            id: 'label-city',
            type: 'symbol',
            source: 'openmaptiles',
            'source-layer': 'place',
            filter: ['in', 'class', 'city', 'municipality'],
            layout: {
              'text-field': ['get', 'name:en'],
              'text-size': 10
            },
            paint: {
              'text-color': '#00FF88',
              'text-halo-color': '#000000',
              'text-halo-width': 1
            }
          }
        ]
      },
      center: [78.9629, 21],
      zoom: 4
    });

    mapRef.current.mapInstance = map;

    return () => map.remove();
  }, []);

  const handleAnalyze = async () => {
    const location = searchQuery.trim();
    if (!location) return;

    setLoading(true);
    setNewsData([]);
    setSummary({});

    // Zoom map to location
    const geo = await fetch(
      `https://api.maptiler.com/geocoding/${encodeURIComponent(location)}.json?key=${mapTilerKey}`
    );
    const geoData = await geo.json();
    if (geoData.features?.length) {
      const [lng, lat] = geoData.features[0].center;
      mapRef.current.mapInstance.flyTo({ center: [lng, lat], zoom: 10 });
    }

    try {
      const res = await fetch('http://localhost:8000/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ location, days: 2 })
      });

      const news = await res.json();

      const filtered = news.filter(item => item.threat !== 'NaN');
      setNewsData(filtered);

      const countByCategory = {};
      filtered.forEach(item => {
        const cat = item.category || 'unknown';
        countByCategory[cat] = (countByCategory[cat] || 0) + 1;
      });
      setSummary(countByCategory);
    } catch (err) {
      console.error("❌ API error:", err);
    }

    setLoading(false);
  };

  async function handleSendChat() {
    if (!chatInput.trim()) return;
    const userMsg = { role: 'user', content: chatInput.trim() };
    const newMessages = [...chatMessages, userMsg];
    setChatMessages(newMessages);
    setChatInput('');
    setChatLoading(true);

    const res = await fetch('http://localhost:11434/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'deepseek-r1:8b',
        prompt: newMessages.map(m => `${m.role === 'user' ? 'User' : 'AI'}: ${m.content}`).join('\n') + '\nAI:',
        stream: false
      })
    });

    const data = await res.json();
    setChatMessages([...newMessages, { role: 'ai', content: data.response.trim() }]);
    setChatLoading(false);
  }

  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative' }}>
      {/* 🔍 Search input and button */}
      <div style={{
        position: 'absolute',
        top: '20px',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 10,
        display: 'flex',
        gap: '8px'
      }}>
        <input
          type="text"
          placeholder="Search location..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={{
            padding: '10px 15px',
            borderRadius: '6px',
            border: 'none',
            backgroundColor: '#111',
            color: '#00FF88',
            fontSize: '16px',
            boxShadow: '0 0 8px #00FF88',
            width: '260px',
            textAlign: 'center'
          }}
        />
        <button
          onClick={handleAnalyze}
          style={{
            padding: '10px 15px',
            borderRadius: '6px',
            border: 'none',
            backgroundColor: '#00FF88',
            color: '#000',
            fontWeight: 'bold',
            boxShadow: '0 0 8px #00FF88',
            cursor: 'pointer'
          }}
        >
          Analyze
        </button>
      </div>

      {/* 📰 News Panel */}
      <div style={{
        position: 'absolute',
        top: '70px',
        right: '20px',
        zIndex: 10,
        width: '360px',
        maxHeight: '75vh',
        overflowY: 'auto',
        padding: '12px',
        backgroundColor: '#111',
        color: '#00FF88',
        borderRadius: '12px',
        boxShadow: '0 0 10px #00FF88',
        fontSize: '14px'
      }}>
        <h3 style={{ marginBottom: '10px', borderBottom: '1px solid #00FF88', paddingBottom: '4px' }}>
          🧠 Classified News
        </h3>
        {loading ? (
          <div>Loading news...</div>
        ) : newsData.length === 0 ? (
          <div>No results yet.</div>
        ) : (
          newsData
            .slice()
            .sort((a, b) => {
              const order = { HIGH: 0, MEDIUM: 1, LOW: 2 };
              return (order[a.threat] ?? 99) - (order[b.threat] ?? 99);
            })
            .map((item, index) => (
              <div key={index} style={{ marginBottom: '12px' }}>
                <div>
                  <strong>[{item.category?.toUpperCase()}]</strong>{" "}
                  <span style={{
                    color:
                      item.threat === 'HIGH' ? '#FF3333' :
                      item.threat === 'MEDIUM' ? '#FFA500' :
                      item.threat === 'LOW' ? '#FFFF00' : '#00FF88',
                    fontWeight: 'bold'
                  }}>
                    ({item.threat})
                  </span>
                </div>
                <div>{item.title}</div>
                <a
                  href={item.link}
                  target="_blank"
                  rel="noreferrer"
                  style={{ color: '#00FF88', textDecoration: 'underline' }}
                >
                  Read more
                </a>
                <div>
                  <button
                    onClick={() => {
                      setChatTitle(item.title);
                      setChatMessages([
                        {
                          role: 'system',
                          content: `You are an assistant helping users explore this news: "${item.title}". Answer their questions.`
                        }
                      ]);
                      setChatOpen(true);
                    }}
                    style={{
                      marginTop: '6px',
                      background: '#00FF88',
                      color: '#000',
                      padding: '5px 10px',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontSize: '13px'
                    }}
                  >
                    Chat
                  </button>
                </div>
              </div>
            ))
        )}
      </div>

      {/* 📊 Summary */}
      <div style={{
        position: 'absolute',
        top: '70px',
        left: '20px',
        zIndex: 10,
        width: '200px',
        padding: '12px',
        backgroundColor: '#111',
        color: '#00FF88',
        borderRadius: '12px',
        boxShadow: '0 0 10px #00FF88',
        fontSize: '14px'
      }}>
        <h3 style={{ marginBottom: '10px', borderBottom: '1px solid #00FF88', paddingBottom: '4px' }}>
          📊 Summary
        </h3>
        {loading ? (
          <div>Loading summary...</div>
        ) : Object.keys(summary).length === 0 ? (
          <div>No data</div>
        ) : (
          Object.entries(summary).map(([cat, count], i) => (
            <div key={i}>{cat.toUpperCase()}: {count}</div>
          ))
        )}
      </div>

      {/* 🗺️ Map */}
      <div ref={mapRef} style={{ width: '100%', height: '100%' }} />

      {/* 💬 Chat Modal */}
      {chatOpen && (
        <div style={{
          position: 'fixed',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          backgroundColor: '#111',
          color: '#00FF88',
          padding: '20px',
          borderRadius: '12px',
          boxShadow: '0 0 15px #00FF88',
          width: '400px',
          maxHeight: '80vh',
          zIndex: 999,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <h3 style={{ marginBottom: '10px', textAlign: 'center' }}>💬 Ask about this article</h3>
          <div style={{ fontStyle: 'italic', marginBottom: '10px', color: '#aaa', textAlign: 'center' }}>{chatTitle}</div>

          <div style={{ maxHeight: '250px', overflowY: 'auto', marginBottom: '10px', width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            {chatMessages.slice(1).map((msg, i) => (
              <div key={i} style={{ marginBottom: '8px', width: '100%', textAlign: 'left' }}>
                <b>{msg.role === 'user' ? 'You' : 'AI'}:</b>{' '}
                <span style={{ wordBreak: 'break-word' }}>
                  <ReactMarkdown>{stripThinking(msg.content)}</ReactMarkdown>
                </span>
              </div>
            ))}
            {chatLoading && <div><i>Thinking...</i></div>}
          </div>

          <div style={{ display: 'flex', width: '100%', gap: '8px' }}>
            <input
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={async (e) => {
                if (e.key === 'Enter' && chatInput.trim()) {
                  await handleSendChat();
                }
              }}
              placeholder="Ask a question..."
              style={{
                flex: 1,
                padding: '8px',
                backgroundColor: '#222',
                color: '#00FF88',
                border: '1px solid #00FF88',
                borderRadius: '6px'
              }}
            />
            <button
              onClick={handleSendChat}
              style={{
                background: '#00FF88',
                color: '#000',
                padding: '8px 16px',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: 'bold',
                fontSize: '15px',
              }}
              disabled={chatLoading || !chatInput.trim()}
            >
              Send
            </button>
          </div>
          <button
            onClick={() => setChatOpen(false)}
            style={{
              marginTop: '10px',
              background: '#333',
              color: '#00FF88',
              padding: '6px 12px',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Close
          </button>
        </div>
      )}
    </div>
  );
}

export default App;
