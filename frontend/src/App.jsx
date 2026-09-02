import React from 'react'
import { Map, ShieldAlert } from 'lucide-react'

function App() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-4">
      <header className="mb-8 flex items-center space-x-3 text-emerald-400">
        <ShieldAlert size={36} />
        <h1 className="text-3xl font-bold tracking-widest">VAYU-CHRONICLE</h1>
      </header>
      <main className="bg-slate-800 p-8 rounded-xl shadow-2xl max-w-2xl w-full text-center border border-slate-700">
        <Map size={48} className="mx-auto text-slate-400 mb-4" />
        <h2 className="text-xl font-semibold mb-2">Tactical Map Interface Offline</h2>
        <p className="text-slate-400 mb-6">
          Geospatial AI backend connection pending...
        </p>
        <button className="px-6 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-md font-medium transition-colors">
          Initialize Uplink
        </button>
      </main>
    </div>
  )
}

export default App
