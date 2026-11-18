import { Outlet, useMatch } from "react-router";

import { PersonList } from "./PersonList";

/**
 * Two panes side by side on wider screens (list + detail).
 * On narrow screens only one pane is visible: the list on "/", otherwise the detail.
 */
export function Layout() {
  const atIndex = useMatch("/") !== null;

  return (
    <div className="mx-auto flex h-dvh max-w-6xl flex-col pt-[env(safe-area-inset-top)] pr-[env(safe-area-inset-right)] pl-[env(safe-area-inset-left)] md:flex-row md:gap-6 md:p-6">
      <aside className={`${atIndex ? "flex" : "hidden"} min-h-0 flex-1 flex-col md:flex md:w-80 md:flex-none`}>
        <PersonList />
      </aside>
      <main className={`${atIndex ? "hidden" : "block"} min-h-0 flex-1 overflow-y-auto md:block`}>
        <Outlet />
      </main>
    </div>
  );
}
