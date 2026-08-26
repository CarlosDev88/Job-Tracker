/** @type {import('tailwindcss').Config} */
export default {
    darkMode: ['selector', '[data-theme="dark"]'],
    content: ['./index.html', './src/**/*.{js,jsx}'],
    theme: {
        extend: {
            fontFamily: {
                sans: ['Manrope', 'system-ui', '-apple-system', 'sans-serif'],
                mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
            },
            colors: {
                paper: 'rgb(var(--color-paper) / <alpha-value>)',
                surface: 'rgb(var(--color-surface) / <alpha-value>)',
                hairline: {
                    DEFAULT: 'rgb(var(--color-hairline) / <alpha-value>)',
                    strong: 'rgb(var(--color-hairline-strong) / <alpha-value>)',
                },
                ink: {
                    primary: 'rgb(var(--color-ink-primary) / <alpha-value>)',
                    secondary: 'rgb(var(--color-ink-secondary) / <alpha-value>)',
                    muted: 'rgb(var(--color-ink-muted) / <alpha-value>)',
                },
                accent: {
                    DEFAULT: 'rgb(var(--color-accent) / <alpha-value>)',
                    hover: 'rgb(var(--color-accent-hover) / <alpha-value>)',
                    muted: 'rgb(var(--color-accent-muted) / <alpha-value>)',
                    text: 'rgb(var(--color-accent-text) / <alpha-value>)',
                },
                positive: {
                    DEFAULT: 'rgb(var(--color-positive) / <alpha-value>)',
                    muted: 'rgb(var(--color-positive-muted) / <alpha-value>)',
                    text: 'rgb(var(--color-positive-text) / <alpha-value>)',
                },
                negative: {
                    DEFAULT: 'rgb(var(--color-negative) / <alpha-value>)',
                    muted: 'rgb(var(--color-negative-muted) / <alpha-value>)',
                    text: 'rgb(var(--color-negative-text) / <alpha-value>)',
                },
            },
            boxShadow: {
                modal: '0 24px 48px -12px rgb(0 0 0 / 0.35)',
                popover: '0 8px 24px -6px rgb(0 0 0 / 0.2)',
            },
        },
    },
    plugins: [],
}
