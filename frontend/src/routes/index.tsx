import { useEffect, useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { getPlan, getContext, getActuals, getContextMarkdown } from '../lib/api'
import { Sidebar } from '../components/Sidebar'
import { RecentActivities } from '../components/RecentActivities'
import { FridgeWeek } from '../components/FridgeWeek'
import { ActivityModal } from '../components/ActivityModal'
import { WeekCard } from '../components/WeekCard'
import { X } from 'lucide-react'
import type { ContextData, Week, Activity } from '../types/schema'

export const Route = createFileRoute('/')({
  component: Dashboard,
})

function Dashboard() {
  const [fridgeWeekId, setFridgeWeekId] = useState<string | null>(null);
  const [selectedActivity, setSelectedActivity] = useState<Activity | null>(null);

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
    queryFn: getPlan 
  })
  
  const { data: context, isLoading: contextLoading } = useQuery({ 
    queryKey: ['context'], 
    queryFn: getContext 
  })

  // Start with a safe default for actuals to avoid breaking if file missing/empty
  const { data: actuals } = useQuery({ 
    queryKey: ['actuals'], 
    queryFn: getActuals,
    initialData: [] 
  })

  const { data: markdown } = useQuery({ 
    queryKey: ['markdown'], 
    queryFn: getContextMarkdown,
    initialData: ''
  })

  if (planLoading || contextLoading) return (
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

  const todayDate = new Date();
  const year = todayDate.getFullYear();
  const month = String(todayDate.getMonth() + 1).padStart(2, '0');
  const day = String(todayDate.getDate()).padStart(2, '0');
  const todayStr = `${year}-${month}-${day}`;

  return (
    <div className={`min-h-screen bg-slate-50 py-8 px-4 sm:px-6 lg:px-8 font-sans ${fridgeWeekId ? 'bg-white print:p-0' : ''}`}>
      {fridgeWeekId && (
        <div className="fixed top-4 right-4 z-50 print:hidden">
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
                                <FridgeWeek week={week} weekIndex={originalIndex} />
                            </div>
                        )
                    }

                    return (
                        <div key={week.weekStarting}>
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
    </div>
  )
}
