import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import ErrorMessage from './ErrorMessage'

describe('ErrorMessage', () => {
  it('announces the error and invokes retry when requested', () => {
    const onRetry = vi.fn()
    render(<ErrorMessage message="Unable to load calls" onRetry={onRetry} />)

    expect(screen.getByRole('alert')).toHaveTextContent('Unable to load calls')
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(onRetry).toHaveBeenCalledOnce()
  })

  it('shows a useful fallback when no message is provided', () => {
    render(<ErrorMessage />)

    expect(screen.getByRole('alert')).toHaveTextContent('An error occurred.')
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
