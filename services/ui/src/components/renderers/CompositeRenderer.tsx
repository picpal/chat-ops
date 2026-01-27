import React, { useMemo } from 'react'
import { CompositeRenderSpec, RenderSpec } from '@/types/renderSpec'
import { QueryResult } from '@/types/queryResult'
import RenderSpecDispatcher from './RenderSpecDispatcher'

interface CompositeRendererProps {
  spec: CompositeRenderSpec
  data: QueryResult
}

const CompositeRenderer: React.FC<CompositeRendererProps> = ({ spec, data }) => {
  // 두 구조 모두 지원: spec.components 또는 spec.composite?.components
  const components = useMemo<RenderSpec[]>(() => {
    if (spec.components && Array.isArray(spec.components)) {
      return spec.components
    }
    // Legacy 구조 지원 (spec.composite.components)
    const legacySpec = spec as CompositeRenderSpec & { composite?: { components?: RenderSpec[] } }
    if (legacySpec.composite?.components && Array.isArray(legacySpec.composite.components)) {
      return legacySpec.composite.components
    }
    return []
  }, [spec])

  if (components.length === 0) {
    return (
      <div className="text-slate-500 text-sm p-4">
        표시할 컴포넌트가 없습니다.
      </div>
    )
  }

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

      {components.map((component, idx) => (
        <div key={`${component.type}-${idx}`} className="animate-fade-in-up" style={{ animationDelay: `${idx * 100}ms` }}>
          <RenderSpecDispatcher renderSpec={component} queryResult={data} />
        </div>
      ))}
    </div>
  )
}

export default CompositeRenderer
