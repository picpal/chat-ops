import React from 'react'
import { RenderSpec, ClarificationRenderSpec } from '@/types/renderSpec'
import { QueryResult } from '@/types/queryResult'
import { useChatStore } from '@/store'
import TableRenderer from './TableRenderer'
import TextRenderer from './TextRenderer'
import ChartRenderer from './ChartRenderer'
import LogRenderer from './LogRenderer'
import CompositeRenderer from './CompositeRenderer'
import ClarificationRenderer from './ClarificationRenderer'

interface RenderSpecDispatcherProps {
  renderSpec: RenderSpec
  queryResult: QueryResult
}

const RenderSpecDispatcher: React.FC<RenderSpecDispatcherProps> = ({
  renderSpec,
  queryResult,
}) => {
  const { handleClarificationSelect } = useChatStore()

  switch (renderSpec.type) {
    case 'table':
      return <TableRenderer spec={renderSpec} data={queryResult} />
    case 'text':
      return <TextRenderer spec={renderSpec} />
    case 'chart':
      return <ChartRenderer spec={renderSpec} data={queryResult} />
    case 'log':
      return <LogRenderer spec={renderSpec} data={queryResult} />
    case 'composite':
      return <CompositeRenderer spec={renderSpec} data={queryResult} />
    case 'clarification':
      return (
        <ClarificationRenderer
          spec={renderSpec as ClarificationRenderSpec}
          onOptionSelect={handleClarificationSelect}
        />
      )
    default:
      return (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-amber-800">
          <p className="font-medium">Unsupported render type</p>
          <p className="text-sm mt-1">
            The render type "{(renderSpec as any).type}" is not supported.
          </p>
        </div>
      )
  }
}

export default RenderSpecDispatcher
