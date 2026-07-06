// >70% verde, >40% amarillo, <=40% rojo — mismo criterio en Dashboard y Feed.
export default function ScoreBadge({ score }) {
    const estilo = score > 70
        ? 'bg-green-950 text-green-400 border-green-900'
        : score > 40
            ? 'bg-yellow-950 text-yellow-400 border-yellow-900'
            : 'bg-red-950 text-red-400 border-red-900'

    return (
        <span className={`text-sm font-mono border px-2 py-1 rounded shrink-0 ${estilo}`}>
            {score}%
        </span>
    )
}
