import React from 'react'
import { cn, getStatusColor } from '@/utils'

interface BadgeProps {
  children: React.ReactNode
  status?: string
  variant?: 'success' | 'error' | 'warning' | 'info' | 'default'
  className?: string
}

const variantClasses = {
  success: 'bg-emerald-50 text-emerald-700 border-emerald-100',
  error: 'bg-red-50 text-red-700 border-red-100',
  warning: 'bg-amber-50 text-amber-700 border-amber-100',
  info: 'bg-blue-50 text-blue-700 border-blue-100',
  default: 'bg-slate-100 text-slate-600 border-slate-200',
}

const Badge: React.FC<BadgeProps> = ({ children, status, variant, className }) => {
  // If status is provided, derive variant from status
  let badgeVariant = variant || 'default'
  if (status && !variant) {
    const color = getStatusColor(status)
    badgeVariant =
      color === 'emerald'
        ? 'success'
        : color === 'red'
        ? 'error'
        : color === 'amber'
        ? 'warning'
        : color === 'blue'
        ? 'info'
        : 'default'
  }

  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-full border text-[10px] font-bold uppercase tracking-wide',
        variantClasses[badgeVariant],
        className
      )}
    >
      {children}
    </span>
  )
}

export default Badge
