import { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

function App() {
  const mapRef = useRef(null);
  const [searchQuery, setSearchQuery] = useState('');

  const mapTilerKey = 'ApoUTstdY1CJFGOL8QLi';

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

  const handleSearch = async (e) => {
    if (e.key === 'Enter' && searchQuery.trim() !== '') {
      const response = await fetch(
        `https://api.maptiler.com/geocoding/${encodeURIComponent(
          searchQuery
        )}.json?key=${mapTilerKey}`
      );
      const data = await response.json();
      if (data.features && data.features.length > 0) {
        const [lng, lat] = data.features[0].center;
        mapRef.current.mapInstance.flyTo({
          center: [lng, lat],
          zoom: 10,
          speed: 1.2
        });
      } else {
        alert('Location not found.');
      }
    }
  };

  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative' }}>
      <input
        type="text"
        placeholder="Search location..."
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        onKeyDown={handleSearch}
        style={{
          position: 'absolute',
          top: '20px',
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 10,
          padding: '10px 15px',
          borderRadius: '6px',
          border: 'none',
          backgroundColor: '#111',
          color: '#00FF88',
          fontSize: '16px',
          boxShadow: '0 0 8px #00FF88',
          width: '300px',
          textAlign: 'center'
        }}
      />
      <div ref={mapRef} style={{ width: '100%', height: '100%' }} />
    </div>
  );
}

export default App;
