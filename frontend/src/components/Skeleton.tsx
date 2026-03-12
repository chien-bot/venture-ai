export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} />;
}

export function ProjectListSkeleton() {
  return (
    <div style={{ borderTop: "1px solid var(--border)" }}>
      {[1, 2, 3].map((i) => (
        <div key={i} className="p-4 space-y-2" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="flex justify-between">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-16" />
          </div>
          <Skeleton className="h-3 w-20" />
        </div>
      ))}
    </div>
  );
}

export function DashboardSkeleton() {
  return (
    <div className="p-8 space-y-6" style={{ background: "var(--bg-base)", height: "100%" }}>
      <div className="flex justify-between items-center">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-9 w-28 rounded-xl" />
      </div>
      <div className="grid grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="glass rounded-2xl p-6 space-y-3">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-10 w-16" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="glass rounded-2xl p-6">
          <Skeleton className="h-4 w-28 mb-4" />
          <Skeleton className="h-48 w-full rounded-xl" />
        </div>
        <div className="glass rounded-2xl p-6 space-y-3">
          <Skeleton className="h-4 w-28 mb-4" />
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-10 w-full rounded-xl" />
          ))}
        </div>
      </div>
    </div>
  );
}
