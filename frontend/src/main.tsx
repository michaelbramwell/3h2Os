import { StrictMode } from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider, createRouter } from '@tanstack/react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from './providers/AuthProvider'

// Import the generated route tree
import { routeTree } from './routeTree.gen'

import './index.css'

// ---------------------------------------------------------------------------
// One-time cleanup of stale credentials from removed integrations.
// The Garmin integration has been removed from the backend, but users may
// still have a `garmin_token` lingering in their browser localStorage. We
// remove it exactly once per browser and record a sentinel so we never
// repeat the work (the token will never be written again).
// ---------------------------------------------------------------------------
const GARMIN_TOKEN_KEY = 'garmin_token';
const GARMIN_TOKEN_REMOVED_FLAG = 'garmin_token_removed';
if (typeof window !== 'undefined' && window.localStorage) {
    if (!window.localStorage.getItem(GARMIN_TOKEN_REMOVED_FLAG)) {
        try {
            window.localStorage.removeItem(GARMIN_TOKEN_KEY);
        } catch {
            // localStorage access can throw in private mode / disabled storage;
            // safe to ignore -- nothing else we can do.
        }
        try {
            window.localStorage.setItem(GARMIN_TOKEN_REMOVED_FLAG, 'true');
        } catch {
            // Same as above; if we can't write the sentinel we'll just retry
            // the remove on the next load, which is harmless.
        }
    }
}

// Create a new router instance
const router = createRouter({
  routeTree,
  context: {
    authentication: undefined! // Will be populated by AuthProvider context if integrated deeper
  }
})

// Register the router instance for type safety
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

const queryClient = new QueryClient()

// Render the app
const rootElement = document.getElementById('root')!
if (!rootElement.innerHTML) {
  const root = ReactDOM.createRoot(rootElement)
  root.render(
    <StrictMode>
      <AuthProvider>
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </AuthProvider>
    </StrictMode>,
  )
}
