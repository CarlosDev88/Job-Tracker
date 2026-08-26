// Para publicaciones del feed: no tienen un score comparable, así que se
// muestra la decisión (REVISAR/TAL_VEZ) como etiqueta, no como medidor.
export default function DecisionBadge({ decision }) {
    const positiva = decision === 'REVISAR'
    const color = positiva ? 'text-positive-text' : 'text-accent-text'
    const punto = positiva ? 'bg-positive' : 'bg-accent'

    return (
        <span className={'inline-flex items-center gap-1.5 font-mono text-[11px] font-medium tracking-wide uppercase ' + color}>
            <span className={'w-1.5 h-1.5 rounded-full ' + punto} />
            {decision}
        </span>
    )
}
