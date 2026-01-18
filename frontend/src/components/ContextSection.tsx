import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ContextSectionProps {
    markdown: string;
}

export function ContextSection({ markdown }: ContextSectionProps) {
    if (!markdown) return <div className="p-4 text-sm text-slate-400 italic">No philosophy loaded...</div>;

    return (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            {/* Using Tailwind Typography plugin prose class */}
            <article className="prose prose-sm prose-slate max-w-none">
                <Markdown remarkPlugins={[remarkGfm]}>{markdown}</Markdown>
            </article>
        </div>
    );
}
