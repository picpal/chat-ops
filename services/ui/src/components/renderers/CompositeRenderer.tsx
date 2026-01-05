import React from 'react'
import { CompositeRenderSpec } from '@/types/renderSpec'
import { QueryResult } from '@/types/queryResult'
import RenderSpecDispatcher from './RenderSpecDispatcher'

interface CompositeRendererProps {
  spec: CompositeRenderSpec
  data: QueryResult
}

const CompositeRenderer: React.FC<CompositeRendererProps> = ({ spec, data }) => {
  return (
    <div className="space-y-6">
      {spec.title && (
        <div className="mb-4">
          <h2 className="text-xl font-bold text-slate-900">{spec.title}</h2>
          {spec.description && (
            <p className="text-slate-500 text-sm mt-1">{spec.description}</p>
          )}
        </div>
      )}

      {spec.components.map((component, idx) => (
        <div key={`${component.type}-${idx}`} className="animate-fade-in-up" style={{ animationDelay: `${idx * 100}ms` }}>
          <RenderSpecDispatcher renderSpec={component} queryResult={data} />
        </div>
      ))}
    </div>
  )
}

export default CompositeRenderer
