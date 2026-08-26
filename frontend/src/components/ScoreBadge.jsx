// Elemento firma de la app: medidor de coincidencia (barra + porcentaje mono).
// >70% verde, >40% ocre (acento), <=40% rojo — mismo criterio en toda la app.
export default function ScoreBadge({ score, compact = false }) {
    const nivel = score > 70 ? 'alto' : score > 40 ? 'medio' : 'bajo'
    const color = { alto: 'bg-positive', medio: 'bg-accent', bajo: 'bg-negative' }[nivel]
    const texto = { alto: 'text-positive-text', medio: 'text-accent-text', bajo: 'text-negative-text' }[nivel]

    return (
        <span className={'inline-flex items-center gap-2 shrink-0' + (compact ? '' : '')}>
            <span className="w-9 h-1.5 rounded-full bg-hairline overflow-hidden">
                <span className={'block h-full rounded-full ' + color} style={{ width: Math.min(100, Math.max(4, score)) + '%' }} />
            </span>
            <span className={'font-mono text-[12.5px] font-medium tabular ' + texto}>{score}%</span>
        </span>
    )
}
