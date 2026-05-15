import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { initGrainTexture } from './lib/noise'
import { App } from './App'
import './index.css'

initGrainTexture()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
