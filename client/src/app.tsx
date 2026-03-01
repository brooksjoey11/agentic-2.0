import { Suspense, lazy } from 'react';
import { Route, Switch } from 'wouter';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { httpBatchLink } from '@trpc/client';
import { trpc } from './lib/trpc.js';
import { AuthProvider } from './contexts/AuthContext.js';
import { ConfigProvider } from './contexts/ConfigContext.js';
import { FeatureFlagProvider } from './contexts/FeatureFlagContext.js';
import { NotificationProvider } from './contexts/NotificationContext.js';
import { ThemeProvider } from './contexts/ThemeContext.js';
import { WebSocketProvider } from './contexts/WebSocketContext.js';
import { ErrorBoundary } from './components/ErrorBoundary.js';
import { Header } from './components/navigation/Header.js';
import { Sidebar } from './components/navigation/Sidebar.js';
import { Toast } from './components/feedback/Toast.js';

// Lazy load pages for code splitting
const Home = lazy(() => import('./pages/Home.js'));
const Admin = lazy(() => import('./pages/admin/Admin.js'));
const Dashboard = lazy(() => import('./pages/dashboard/index.js'));
const Login = lazy(() => import('./pages/auth/login.js'));
const Callback = lazy(() => import('./pages/auth/callback.js'));
const NotFound = lazy(() => import('./pages/errors/NotFound.js'));
const Profile = lazy(() => import('./pages/dashboard/profile.js'));
const Submissions = lazy(() => import('./pages/dashboard/submissions.js'));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const trpcClient = trpc.createClient({
  links: [
    httpBatchLink({
      url: '/trpc',
      headers: () => {
        const token = localStorage.getItem('auth-token');
        return token ? { Authorization: `Bearer ${token}` } : {};
      },
    }),
  ],
});

function App() {
  return (
    <ErrorBoundary>
      <trpc.Provider client={trpcClient} queryClient={queryClient}>
        <QueryClientProvider client={queryClient}>
          <ThemeProvider defaultTheme="light">
            <AuthProvider>
              <ConfigProvider>
                <FeatureFlagProvider>
                  <NotificationProvider>
                    <WebSocketProvider>
                      <div className="min-h-screen bg-white font-sans">
                        <Header />
                        <div className="flex">
                          <Sidebar />
                          <main className="flex-1 p-8">
                            <Suspense fallback={<div className="flex items-center justify-center h-64">
                              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900" />
                            </div>}>
                              <Switch>
                                <Route path="/" component={Home} />
                                <Route path="/login" component={Login} />
                                <Route path="/auth/callback" component={Callback} />
                                <Route path="/dashboard" component={Dashboard} />
                                <Route path="/profile" component={Profile} />
                                <Route path="/submissions" component={Submissions} />
                                <Route path="/admin/:tab*" component={Admin} />
                                <Route component={NotFound} />
                              </Switch>
                            </Suspense>
                          </main>
                        </div>
                        <Toast />
                      </div>
                    </WebSocketProvider>
                  </NotificationProvider>
                </FeatureFlagProvider>
              </ConfigProvider>
            </AuthProvider>
          </ThemeProvider>
        </QueryClientProvider>
      </trpc.Provider>
    </ErrorBoundary>
  );
}

export default App;