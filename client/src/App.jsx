function App() {
  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col items-center justify-center p-4">
      <div className="bg-gray-800 p-8 rounded-2xl shadow-2xl border border-gray-700 text-center max-w-md w-full animate-in fade-in zoom-in duration-500">
        <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
          Vite + React + Tailwind
        </h1>
        <p className="text-gray-400 mb-6 text-lg">
          Setup successful! Tailwind CSS v4 is now active.
        </p>
        <div className="flex flex-wrap gap-3 justify-center">
          <span className="px-4 py-2 bg-blue-500/10 text-blue-400 rounded-full border border-blue-500/20 text-sm font-medium">
            React
          </span>
          <span className="px-4 py-2 bg-purple-500/10 text-purple-400 rounded-full border border-purple-500/20 text-sm font-medium">
            Vite
          </span>
          <span className="px-4 py-2 bg-teal-500/10 text-teal-400 rounded-full border border-teal-500/20 text-sm font-medium">
            Tailwind v4
          </span>
        </div>
      </div>
    </div>
  )
}

export default App
