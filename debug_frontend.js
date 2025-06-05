
// Production vs Debug mode
const API_DEBUG = process.env.NODE_ENV === 'development';

const sendChatMessage = async (prompt) => {
  const response = await fetch(`/chat?debug=${API_DEBUG}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: `prompt=${encodeURIComponent(prompt)}`
  });
  
  return await response.json();
};

// Debug panel (only in development)
const DebugPanel = ({ debugData }) => {
  if (!API_DEBUG || !debugData) return null;
  
  return (
    <div className="debug-panel">
      <h3>Debug Info</h3>
      <pre>{JSON.stringify(debugData, null, 2)}</pre>
    </div>
  );
};
