// Vacante con intención ambigua (linkedin_publicaciones sin señal clara de
// oferta/candidato/ruido social): no se puntúa, se marca para revisión manual.
export default function RevisarBadge() {
    return (
        <span className="inline-flex items-center gap-1.5 font-mono text-[11px] font-medium tracking-wide uppercase text-ink-secondary">
            <span className="w-1.5 h-1.5 rounded-full bg-ink-muted" />
            Revisar
        </span>
    )
}
