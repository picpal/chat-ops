import React from 'react'
import { cn } from '@/utils'
import Icon from './Icon'

interface ButtonProps {
  children: React.ReactNode
  onClick?: () => void
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  icon?: string
  iconPosition?: 'left' | 'right'
  disabled?: boolean
  className?: string
  type?: 'button' | 'submit' | 'reset'
}

const variantClasses = {
  primary:
    'bg-primary hover:bg-blue-600 active:bg-blue-700 text-white shadow-md shadow-blue-500/20',
  secondary:
    'bg-white hover:bg-slate-50 border border-slate-200 text-slate-600 shadow-sm',
  ghost: 'hover:bg-slate-100 text-slate-600',
  danger: 'bg-red-500 hover:bg-red-600 active:bg-red-700 text-white',
}

const sizeClasses = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2.5 text-sm',
  lg: 'px-6 py-3 text-base',
}

const Button: React.FC<ButtonProps> = ({
  children,
  onClick,
  variant = 'primary',
  size = 'md',
  icon,
  iconPosition = 'left',
  disabled = false,
  className,
  type = 'button',
}) => {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-colors',
        variantClasses[variant],
        sizeClasses[size],
        disabled && 'opacity-50 cursor-not-allowed',
        className
      )}
    >
      {icon && iconPosition === 'left' && <Icon name={icon} size="sm" />}
      {children}
      {icon && iconPosition === 'right' && <Icon name={icon} size="sm" />}
    </button>
  )
}

export default Button
