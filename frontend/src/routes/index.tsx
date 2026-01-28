import { useEffect, useState, useMemo } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { getPlan, getContext, getActuals, getContextMarkdown } from '../lib/api'
import { Sidebar } from '../components/Sidebar'
import { RecentActivities } from '../components/RecentActivities'
import { FridgeWeek } from '../components/FridgeWeek'
import { ActivityModal } from '../components/ActivityModal'
import { WeekCard } from '../components/WeekCard'
import { GarminSettings } from '../components/GarminSettings'
import { CreatePlanDialog } from '../components/CreatePlanDialog'
import { PlanSwitcher } from '../components/PlanSwitcher'
import { X, Plus } from 'lucide-react'
import type { ContextData, Week, Activity } from '../types/schema'

export const Route = createFileRoute('/')({
  component: Dashboard,
})

import { useAuth } from 'react-oidc-context'

function Dashboard() {
  const auth = useAuth();
  const [fridgeWeekId, setFridgeWeekId] = useState<string | null>(null);
  const [selectedActivity, setSelectedActivity] = useState<Activity | null>(null);
  const [showCreatePlan, setShowCreatePlan] = useState(false);

  useEffect(() => {
    // Optional: Log auth status
    if (auth.isAuthenticated) {
        console.log("Authenticated as", auth.user?.profile.preferred_username);
    }
  }, [auth.isAuthenticated, auth.user]);

  // Handle Login/Logout UI in Sidebar or Header?
  // Ideally, we pass auth state to Sidebar.


  useEffect(() => {
    if (fridgeWeekId) {
        // Allow time for render
        const timer = setTimeout(() => {
            window.print();
        }, 100);
        return () => clearTimeout(timer);
    }
  }, [fridgeWeekId]);

  const { data: plan, isLoading: planLoading, error: planError } = useQuery({ 
    queryKey: ['plan'], 
    queryFn: getPlan,
    enabled: auth.isAuthenticated 
  })
  
  const { data: context, isLoading: contextLoading } = useQuery({ 
    queryKey: ['context'], 
    queryFn: getContext,
    enabled: auth.isAuthenticated 
  })

  // Start with a safe default for actuals to avoid breaking if file missing/empty
  const { data: actuals, isLoading: actualsLoading } = useQuery({ 
    queryKey: ['actuals'], 
    queryFn: getActuals,
    enabled: auth.isAuthenticated
  })

  const { data: markdown } = useQuery({ 
    queryKey: ['markdown'], 
    queryFn: getContextMarkdown,
    initialData: '',
    enabled: auth.isAuthenticated
  })

  // Calculate todayStr here so it's available for the effect
  // Use useMemo to ensure todayStr reference is stable (though string primitives are equal by value, this satisfies linter/reviews)
  const todayStr = useMemo(() => {
    const todayDate = new Date();
    const year = todayDate.getFullYear();
    const month = String(todayDate.getMonth() + 1).padStart(2, '0');
    const day = String(todayDate.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }, []); // Empty dependency array means it's calculated once on mount (or you could depend on nothing and let it recalc, but useMemo signals intent)

  // Auto-scroll to current week using robust string comparison
  useEffect(() => {
    if (plan && !fridgeWeekId && !actualsLoading) {
      // Find the latest week that has started (weekStarting <= todayStr)
      // Assuming plan is sorted ascending by date
      const currentWeek = [...plan].reverse().find((w: Week) => todayStr >= w.weekStarting);

      if (currentWeek) {
          setTimeout(() => {
              const el = document.getElementById(`week-${currentWeek.weekStarting}`);
              if (el) {
                  el.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }
          }, 300);
      }
    }
  }, [plan, fridgeWeekId, actualsLoading, todayStr]);

  if (auth.isLoading) {
      return (
        <div className="flex h-screen items-center justify-center bg-slate-50">
            <div className="text-center">
                <div className="w-8 h-8 border-4 border-slate-200 border-t-blue-500 rounded-full animate-spin mx-auto mb-4"></div>
                <p className="text-slate-500 font-medium">Authenticating...</p>
            </div>
        </div>
      )
  }

  if (!auth.isAuthenticated) {
      return (
        <div className="flex h-screen items-center justify-center bg-slate-50">
            <div className="text-center">
                <h1 className="text-2xl font-bold mb-4">3h2Os Training Plan</h1>
                <p className="text-slate-500 mb-6">Please login to view your training plan.</p>
                {auth.error && (
                    <div className="mb-4 p-3 bg-red-100 text-red-700 rounded-md text-sm max-w-md mx-auto">
                        Authentication Error: {auth.error.message}
                    </div>
                )}
                <button 
                onClick={() => auth.signinRedirect().catch(e => alert("Login failed: " + e))}
                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-full font-bold shadow-lg transition"
                >
                Login using Keycloak
                </button>
            </div>
        </div>
      )
  }

  if (planLoading || contextLoading || actualsLoading) return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
          <div className="text-center">
              <div className="w-8 h-8 border-4 border-slate-200 border-t-orange-500 rounded-full animate-spin mx-auto mb-4"></div>
              <p className="text-slate-500 font-medium">Loading training data...</p>
          </div>
      </div>
  )

  if (planError) return <div className="p-8 text-center text-red-500">Error loading plan: {planError.message}</div>
  if (!plan || !context) return null

  // Filter if in Fridge Mode
  const visibleWeeks = fridgeWeekId 
    ? plan.filter((w: Week) => w.weekStarting === fridgeWeekId)
    : plan;

  return (
    <div className={`min-h-screen bg-slate-50 py-8 px-4 sm:px-6 lg:px-8 font-sans ${fridgeWeekId ? 'bg-white print:p-0' : ''}`}>
      <div className="absolute top-4 right-4 z-50 flex gap-2 print:hidden">
         {auth.isAuthenticated ? (
             <div className="flex items-center gap-2 bg-white/50 backdrop-blur px-3 py-1.5 rounded-full border border-slate-200">
                 <button
                    onClick={() => setShowCreatePlan(true)}
                    className="p-1 hover:bg-slate-200 rounded-full text-blue-600 transition"
                    title="Create New Plan"
                 >
                    <Plus size={18} />
                 </button>
                 <div className="h-4 w-px bg-slate-300 mx-1"></div>
                 <PlanSwitcher />
                 <div className="h-4 w-px bg-slate-300 mx-1"></div>
                 <GarminSettings />
                 <span className="text-xs text-slate-500 font-medium border-l border-slate-300 pl-2">
                    {auth.user?.profile.preferred_username || "User"}
                 </span>
                 <button 
                    onClick={() => auth.removeUser()}
                    className="text-xs text-red-500 hover:text-red-700 font-bold ml-1"
                 >
                    Logout
                 </button>
             </div>
         ) : (
             <button 
                onClick={() => auth.signinRedirect()}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-full text-xs font-bold shadow-sm transition"
             >
                Login
             </button>
         )}
      </div>

      {fridgeWeekId && (
        <div className="fixed top-4 right-4 z-50 print:hidden mr-20"> {/* Adjusted margin to avoid overlap */}
            <button 
                onClick={() => setFridgeWeekId(null)}
                className="flex items-center gap-2 bg-slate-900 text-white px-4 py-2 rounded-full shadow-lg hover:bg-slate-700 transition"
            >
                <X size={16} /> Exit Fridge Mode
            </button>
        </div>
      )}

      <div className="max-w-[1600px] mx-auto">
        
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 xl:gap-8">
            
            {/* Sidebar Column - Hide in Fridge Mode */}
            {!fridgeWeekId && (
                <div className="lg:col-span-1 space-y-6">
                    <Sidebar context={context as ContextData} markdown={markdown} />
                    {/* RecentActivities moved to be a child of Sidebar or separate is fine, but user complained about "under" */}
                    <RecentActivities activities={actuals as Activity[]} />
                </div>
            )}

            {/* Main Content Column */}
            <div className={`${fridgeWeekId ? 'col-span-1 lg:col-span-4 max-w-[210mm] mx-auto w-full' : 'lg:col-span-3'} space-y-6`}>
                {visibleWeeks.map((week: Week) => {
                    // Match original index in plan
                    const originalIndex = plan.findIndex((w: Week) => w.weekStarting === week.weekStarting);
                    
                    if (fridgeWeekId === week.weekStarting) {
                        return (
                            <div key={week.weekStarting}>
                                <FridgeWeek week={week} weekIndex={originalIndex} context={context as ContextData} />
                            </div>
                        )
                    }

                    return (
                        <div key={week.weekStarting} id={`week-${week.weekStarting}`} className="scroll-mt-4">
                             <WeekCard
                                week={week}
                                actuals={actuals as Activity[]}
                                todayStr={todayStr}
                                isFridgeMode={!!fridgeWeekId}
                                onFridgeClick={setFridgeWeekId}
                                onActivityClick={setSelectedActivity}
                             />
                        </div>
                    )
                })}
            </div>
        </div>
      </div>

      {selectedActivity && (
        <ActivityModal 
            activity={selectedActivity} 
            onClose={() => setSelectedActivity(null)} 
        />
      )}

      {showCreatePlan && (
        <CreatePlanDialog onClose={() => setShowCreatePlan(false)} />
      )}
    </div>
  )
}
