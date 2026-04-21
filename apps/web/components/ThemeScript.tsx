/**
 * Inline theme bootstrap. Runs before hydration to avoid flash-of-wrong-theme.
 * Reads the same localStorage key as <ThemeToggle /> and toggles the `dark`
 * class on <html> accordingly. Rendered inside <body> at the very top.
 */
export function ThemeScript() {
  const code = `(() => {
    try {
      var stored = localStorage.getItem('omlorsnewsbot:theme');
      var theme = stored || 'system';
      var prefersDark = theme === 'dark' ||
        (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
      document.documentElement.classList.toggle('dark', prefersDark);
      document.documentElement.dataset.theme = theme;
    } catch (e) {}
  })();`;
  return <script dangerouslySetInnerHTML={{ __html: code }} />;
}
