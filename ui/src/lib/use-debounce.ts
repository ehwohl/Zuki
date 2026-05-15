import { useRef, useCallback } from 'react'

export function useDebounce<A extends unknown[]>(fn: (...args: A) => void, delay: number) {
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  return useCallback(
    (...args: A) => {
      if (timer.current) clearTimeout(timer.current)
      timer.current = setTimeout(() => fn(...args), delay)
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [delay],
  )
}
