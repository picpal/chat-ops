import React, { useState } from 'react'

interface StarRatingProps {
  rating: number
  onRate?: (rating: number) => void
  size?: 'sm' | 'md' | 'lg'
  readonly?: boolean
}

const sizeMap = {
  sm: 20,
  md: 24,
  lg: 28,
}

const StarRating: React.FC<StarRatingProps> = ({
  rating,
  onRate,
  size = 'sm',
  readonly = false,
}) => {
  const [hoverRating, setHoverRating] = useState(0)
  const iconSize = sizeMap[size]

  const handleClick = (star: number) => {
    if (readonly || !onRate) return
    onRate(star)
  }

  const displayRating = hoverRating || rating

  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          disabled={readonly}
          onClick={() => handleClick(star)}
          onMouseEnter={() => !readonly && setHoverRating(star)}
          onMouseLeave={() => !readonly && setHoverRating(0)}
          className={`p-0 border-0 bg-transparent cursor-pointer transition-colors ${
            readonly ? 'cursor-default' : 'hover:scale-110'
          }`}
          style={{ lineHeight: 0 }}
        >
          <span
            className={`material-symbols-outlined ${
              star <= displayRating ? 'text-amber-400' : 'text-slate-300'
            }`}
            style={{
              fontSize: iconSize,
              fontVariationSettings: star <= displayRating
                ? "'FILL' 1, 'wght' 400"
                : "'FILL' 0, 'wght' 400",
            }}
          >
            star
          </span>
        </button>
      ))}
    </div>
  )
}

export default StarRating
