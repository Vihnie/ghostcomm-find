import { useEffect, useRef } from 'react'
import { X } from 'lucide-react'

export default function Modal({ title, onClose, children }) {
  const dialog = useRef(null)
  useEffect(() => {
    const element = dialog.current
    const previous = document.activeElement
    element.showModal()
    return () => {
      element.close()
      previous?.focus()
    }
  }, [])
  return (
    <dialog className="modal connected-modal" ref={dialog} onCancel={event => {
      event.preventDefault()
      onClose()
    }} aria-labelledby="dialog-title">
      <button className="modal-close" aria-label="Close dialog" onClick={onClose}><X /></button>
      <h2 id="dialog-title">{title}</h2>
      {children}
    </dialog>
  )
}
