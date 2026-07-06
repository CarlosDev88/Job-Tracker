// Para vacantes del feed clasificadas por feed_filter.py (algoritmo_feed.md):
// su score no es un porcentaje comparable al de keywords.py, así que se
// muestra la decisión (REVISAR/TAL_VEZ) en vez de forzarla por ScoreBadge.
export default function DecisionBadge({ decision }) {
    const estilo = decision === 'REVISAR'
        ? 'bg-green-950 text-green-400 border-green-900'
        : 'bg-yellow-950 text-yellow-400 border-yellow-900'

    return (
        <span className={`text-sm border px-2 py-1 rounded shrink-0 ${estilo}`}>
            {decision}
        </span>
    )
}
