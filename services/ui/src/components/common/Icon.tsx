import React from 'react'
import { cn } from '@/utils'

interface IconProps {
  name: string
  className?: string
  size?: 'sm' | 'md' | 'lg'
  onClick?: () => void
}

const sizeClasses = {
  sm: 'text-[16px]',
  md: 'text-[20px]',
  lg: 'text-[24px]',
}

const Icon: React.FC<IconProps> = ({ name, className, size = 'md', onClick }) => {
  return (
    <span
      className={cn('material-symbols-outlined', sizeClasses[size], className)}
      onClick={onClick}
      style={onClick ? { cursor: 'pointer', pointerEvents: 'auto' } : undefined}
    >
      {name}
    </span>
  )
}

export default Icon
