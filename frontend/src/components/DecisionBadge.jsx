// Para publicaciones del feed: no tienen un score comparable, así que se
// muestra la decisión (REVISAR/TAL_VEZ) como etiqueta, no como medidor.
const ETIQUETAS = { REVISAR: 'REVISAR', TAL_VEZ: 'TAL VEZ' }

export default function DecisionBadge({ decision }) {
    // Si el detalle guardado no trae decisión (JSON de la fila ilegible), se
    // dice "sin clasificar" en gris: antes se pintaba un punto de color con la
    // etiqueta vacía, que aparentaba una decisión que nunca se tomó.
    const conocida = decision in ETIQUETAS
    const color = !conocida ? 'text-ink-muted' : decision === 'REVISAR' ? 'text-positive-text' : 'text-accent-text'
    const punto = !conocida ? 'bg-ink-muted' : decision === 'REVISAR' ? 'bg-positive' : 'bg-accent'

    return (
        <span className={'inline-flex items-center gap-1.5 font-mono text-[11px] font-medium tracking-wide uppercase ' + color}>
            <span className={'w-1.5 h-1.5 rounded-full ' + punto} />
            {conocida ? ETIQUETAS[decision] : 'sin clasificar'}
        </span>
    )
}
