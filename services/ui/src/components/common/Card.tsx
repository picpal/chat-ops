import React from 'react'
import { cn } from '@/utils'

interface CardProps {
  children: React.ReactNode
  className?: string
  title?: string
  subtitle?: string
  icon?: string
  actions?: React.ReactNode
}

const Card: React.FC<CardProps> = ({
  children,
  className,
  title,
  subtitle,
  icon,
  actions,
}) => {
  return (
    <div
      className={cn(
        'bg-white border border-slate-200 rounded-xl overflow-hidden shadow-lg shadow-slate-200/50',
        className
      )}
    >
      {(title || subtitle || icon || actions) && (
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50/50">
          <div className="flex items-center gap-3">
            {icon && (
              <div className="p-1.5 rounded bg-white text-slate-500 border border-slate-200 shadow-sm">
                <span className="material-symbols-outlined text-[20px]">{icon}</span>
              </div>
            )}
            {(title || subtitle) && (
              <div>
                {title && <h3 className="text-slate-800 text-sm font-bold">{title}</h3>}
                {subtitle && <p className="text-slate-500 text-xs">{subtitle}</p>}
              </div>
            )}
          </div>
          {actions && <div className="flex gap-2">{actions}</div>}
        </div>
      )}
      <div className="p-6">{children}</div>
    </div>
  )
}

export default Card
