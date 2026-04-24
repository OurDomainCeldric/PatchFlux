import { useTranslations } from "next-intl";

export function NewsletterSubscribe() {
  const t = useTranslations("newsletter");
  
  return (
    <section className="mb-6 rounded-lg border border-indigo-200 bg-indigo-50/50 p-4 dark:border-indigo-900/50 dark:bg-indigo-950/20">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex-1">
          <h2 className="text-sm font-bold text-indigo-900 dark:text-indigo-100 flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2005/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-indigo-600 dark:text-indigo-400">
              <path d="M3 4a2 2 0 0 0-2 2v1.161l8.441 4.221a1.25 1.25 0 0 0 1.118 0L19 7.162V6a2 2 0 0 0-2-2H3Z" />
              <path d="m19 8.839-7.77 3.885a2.75 2.75 0 0 1-2.46 0L1 8.839V14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V8.839Z" />
            </svg>
            {t("heading")}
          </h2>
          <p className="mt-1 text-xs text-indigo-800 dark:text-indigo-300">
            {t("description")}
          </p>
        </div>
        
        {/* ACTION REQUIRED: Ersetze "DEIN_BUTTONDOWN_NAME" mit deinem tatsächlichen Accountnamen */}
        <form
          action="https://buttondown.com/api/emails/embed-subscribe/DEIN_BUTTONDOWN_NAME"
          method="post"
          target="popupwindow"
          className="flex w-full sm:w-auto items-center gap-2"
        >
          <input type="hidden" value="1" name="embed" />
          <label htmlFor="newsletter-email" className="sr-only">{t("placeholder")}</label>
          <input
            type="email"
            id="newsletter-email"
            name="email"
            placeholder={t("placeholder")}
            required
            className="flex-1 min-w-[200px] rounded-md border border-indigo-300 bg-white px-3 py-1.5 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 dark:border-indigo-800 dark:bg-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400"
          />
          <button
            type="submit"
            className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 dark:focus:ring-offset-zinc-900 whitespace-nowrap"
          >
            {t("button")}
          </button>
        </form>
      </div>
      <p className="mt-3 text-[10px] text-indigo-600/70 dark:text-indigo-400/50 leading-relaxed">
        {t("disclaimer")}
      </p>
    </section>
  );
}
