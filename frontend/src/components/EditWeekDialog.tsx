import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { X, Calendar } from 'lucide-react'
import type { Week } from '../types/schema'

interface EditWeekDialogProps {
    week?: Week
    isOpen: boolean
    onOpenChange: (open: boolean) => void
    onSave: (id: number, data: { status: string; weekStarting?: string }) => void
}

export function EditWeekDialog({ week, isOpen, onOpenChange, onSave }: EditWeekDialogProps) {
    const [status, setStatus] = useState('normal')
    const [weekStarting, setWeekStarting] = useState('')

    useEffect(() => {
        if (week) {
            setStatus(week.status || 'normal')
            setWeekStarting(week.weekStarting)
        }
    }, [week])

    const handleSave = () => {
        if (!week?.id) {
            console.error("Cannot edit week without ID", week);
            return;
        }
        // Only send status, as weekStarting is read-only logic
        onSave(week.id, { status })
        onOpenChange(false)
    }

    if (!isOpen) return null

    return createPortal(
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="w-full max-w-md bg-white rounded-lg shadow-xl overflow-hidden border border-slate-200">
                <div className="flex items-center justify-between p-4 border-b border-slate-100">
                    <h2 className="text-lg font-semibold text-slate-900">Edit Week</h2>
                    <button onClick={() => onOpenChange(false)} className="text-slate-400 hover:text-slate-600">
                        <X size={20} />
                    </button>
                </div>
                
                <div className="p-4 space-y-4">
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-700">Week Status</label>
                        <select 
                            value={status} 
                            onChange={(e) => setStatus(e.target.value)}
                            className="w-full p-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="normal">Normal</option>
                            <option value="recovery">Recovery</option>
                            <option value="taper">Taper</option>
                            <option value="race">Race Week</option>
                            <option value="marathon">Marathon Week</option>
                            <option value="peak">Peak</option>
                            <option value="base">Base</option>
                        </select>
                    </div>

                    <div className="space-y-2">
                         <div className="flex items-center gap-2 mb-1">
                             <Calendar size={14} className="text-slate-400" />
                             <label className="text-sm font-medium text-slate-700">Start Date (Read Only)</label>
                         </div>
                         <div className="w-full p-2 bg-slate-50 border border-slate-200 rounded-md text-slate-500">
                             {weekStarting}
                         </div>
                         <p className="text-xs text-slate-400">Week start dates are managed automatically by the plan logic.</p>
                    </div>
                </div>

                <div className="p-4 bg-slate-50 flex justify-end gap-2 border-t border-slate-100">
                    <button 
                        onClick={() => onOpenChange(false)}
                        className="px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200 rounded-md transition-colors"
                    >
                        Cancel
                    </button>
                    <button 
                        onClick={handleSave}
                        className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
                    >
                        Save Changes
                    </button>
                </div>
            </div>
        </div>,
        document.body
    )
}
