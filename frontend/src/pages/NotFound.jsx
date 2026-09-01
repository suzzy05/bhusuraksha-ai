import { Link } from "react-router-dom"

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-6 py-20 text-center dark:border-slate-700 dark:bg-slate-900">
      <div className="text-4xl font-bold text-slate-300 dark:text-slate-700">404</div>
      <div className="text-sm font-semibold text-slate-800 dark:text-slate-200">Page not found</div>
      <p className="max-w-md text-sm text-slate-500 dark:text-slate-400">The page you are looking for does not exist.</p>
      <Link
        to="/"
        className="mt-3 rounded-md border border-slate-200 bg-white px-4 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
      >
        Return to Dashboard
      </Link>
    </div>
  )
}
