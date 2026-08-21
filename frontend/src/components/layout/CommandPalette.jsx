import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  Search,
  LayoutDashboard,
  Users,
  Truck,
  FileText,
  FileSignature,
  Package,
  ListChecks,
  Plus,
  ArrowRight,
  X,
  Loader2,
  UserRound,
  Receipt,
  Boxes,
  FileCheck,
} from "lucide-react";

import { useLanguage } from "../../i18n";
import { api } from "../../lib/apiClient";


const COMMANDS = [
  {
    id: "dashboard",
    labelKey: "dashboard",
    fallback: "Dashboard",
    path: "/",
    icon: LayoutDashboard,
    type: "navigation",
  },

  {
    id: "clients",
    labelKey: "clients",
    fallback: "Clients",
    path: "/clients",
    icon: Users,
    type: "navigation",
  },

  {
    id: "suppliers",
    labelKey: "suppliers",
    fallback: "Suppliers",
    path: "/suppliers",
    icon: Truck,
    type: "navigation",
  },

  {
    id: "finance",
    labelKey: "finance",
    fallback: "Finance",
    path: "/finance",
    icon: FileText,
    type: "navigation",
  },

  {
    id: "contracts",
    labelKey: "contracts",
    fallback: "Contracts",
    path: "/contracts",
    icon: FileSignature,
    type: "navigation",
  },

  {
    id: "products",
    labelKey: "products",
    fallback: "Products",
    path: "/products",
    icon: Package,
    type: "navigation",
  },

  {
    id: "tasks",
    labelKey: "tasks",
    fallback: "Tasks",
    path: "/tasks",
    icon: ListChecks,
    type: "navigation",
  },

  {
    id: "create-client",
    labelKey: "createClient",
    fallback: "Create Client",
    path: "/clients?action=create",
    icon: Plus,
    type: "action",
  },

  {
    id: "create-supplier",
    labelKey: "createSupplier",
    fallback: "Create Supplier",
    path: "/suppliers?action=create",
    icon: Plus,
    type: "action",
  },

  {
    id: "create-invoice",
    labelKey: "createInvoice",
    fallback: "Create Invoice",
    path: "/finance?action=create-invoice",
    icon: Plus,
    type: "action",
  },

  {
    id: "create-quote",
    labelKey: "createQuote",
    fallback: "Create Quote",
    path: "/finance?action=create-quote",
    icon: Plus,
    type: "action",
  },

  {
    id: "create-task",
    labelKey: "createTask",
    fallback: "Create Task",
    path: "/tasks?action=create",
    icon: Plus,
    type: "action",
  },
];


const SEARCH_TYPES = {
  clients: {
    labelKey: "clients",
    fallback: "Clients",
    icon: UserRound,
  },

  suppliers: {
    labelKey: "suppliers",
    fallback: "Suppliers",
    icon: Truck,
  },

  products: {
    labelKey: "products",
    fallback: "Products",
    icon: Boxes,
  },

  invoices: {
    labelKey: "invoices",
    fallback: "Invoices",
    icon: Receipt,
  },

  quotes: {
    labelKey: "quotes",
    fallback: "Quotes",
    icon: FileCheck,
  },
};


function getSearchResultId(item) {
  return (
    item?.id ||
    item?._id ||
    item?.client_id ||
    item?.supplier_id ||
    item?.product_id ||
    item?.invoice_id ||
    item?.quote_id
  );
}


function getResultTitle(type, item) {
  if (!item) {
    return "";
  }

  if (type === "clients") {
    return (
      item.name ||
      item.company ||
      item.contact_person ||
      item.email ||
      "Client"
    );
  }

  if (type === "suppliers") {
    return (
      item.name ||
      item.company ||
      item.contact_person ||
      item.email ||
      "Supplier"
    );
  }

  if (type === "products") {
    return (
      item.name ||
      item.sku ||
      item.category ||
      "Product"
    );
  }

  if (type === "invoices") {
    return (
      item.number ||
      item.invoice_number ||
      item.client_name ||
      "Invoice"
    );
  }

  if (type === "quotes") {
    return (
      item.number ||
      item.quote_number ||
      item.client_name ||
      "Quote"
    );
  }

  return item.name || item.title || item.number || "Result";
}


function getResultSubtitle(type, item) {
  if (!item) {
    return "";
  }

  if (type === "clients") {
    return (
      item.company ||
      item.email ||
      item.phone ||
      ""
    );
  }

  if (type === "suppliers") {
    return (
      item.company ||
      item.email ||
      item.phone ||
      item.kvk_number ||
      ""
    );
  }

  if (type === "products") {
    if (item.sku) {
      return `SKU: ${item.sku}`;
    }

    if (item.category) {
      return item.category;
    }

    return item.kind || "";
  }

  if (type === "invoices") {
    return (
      item.client_name ||
      item.status ||
      item.reference ||
      ""
    );
  }

  if (type === "quotes") {
    return (
      item.client_name ||
      item.status ||
      item.reference ||
      ""
    );
  }

  return "";
}


function getResultPath(type, item) {
  const id = getSearchResultId(item);

  if (type === "clients" && id) {
    return `/clients/${id}`;
  }

  if (type === "suppliers" && id) {
    return `/suppliers/${id}`;
  }

  /*
   * Products currently don't have a detail route.
   * Open the Products page instead.
   */
  if (type === "products") {
    return "/products";
  }

  /*
   * Finance currently handles invoices and quotes
   * through the Finance page.
   */
  if (type === "invoices") {
    return id
      ? `/finance?invoice=${encodeURIComponent(id)}`
      : "/finance";
  }

  if (type === "quotes") {
    return id
      ? `/finance?quote=${encodeURIComponent(id)}`
      : "/finance";
  }

  return "/";
}


function buildSearchResults(data, t) {
  const groups = [];

  Object.entries(SEARCH_TYPES).forEach(
    ([type, config]) => {
      const items = Array.isArray(data?.[type])
        ? data[type]
        : [];

      if (!items.length) {
        return;
      }

      const label = config.labelKey
        ? t(config.labelKey)
        : config.fallback;

      items.forEach((item) => {
        groups.push({
          id: `search-${type}-${getSearchResultId(item)}`,
          type: "search",
          searchType: type,
          label: getResultTitle(type, item),
          subtitle: getResultSubtitle(type, item),
          groupLabel: label || config.fallback,
          icon: config.icon,
          path: getResultPath(type, item),
          raw: item,
        });
      });
    }
  );

  return groups;
}


export default function CommandPalette({
  open,
  onClose,
}) {
  const navigate = useNavigate();
  const { t } = useLanguage();

  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);

  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState(false);


  /*
   * Close with Escape.
   */
  useEffect(() => {
    if (!open) {
      return;
    }

    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener(
      "keydown",
      handleKeyDown
    );

    return () => {
      window.removeEventListener(
        "keydown",
        handleKeyDown
      );
    };
  }, [open, onClose]);


  /*
   * Focus when opened.
   */
  useEffect(() => {
    if (!open) {
      return;
    }

    setQuery("");
    setSelectedIndex(0);
    setSearchResults([]);
    setSearchError(false);

    const timer = setTimeout(() => {
      document
        .getElementById(
          "command-palette-search"
        )
        ?.focus();
    }, 20);

    return () => {
      clearTimeout(timer);
    };
  }, [open]);


  /*
   * Translate commands.
   */
  const commands = useMemo(() => {
    return COMMANDS.map((command) => {
      let label =
        command.fallback;

      if (command.labelKey) {
        label =
          t(command.labelKey) ||
          command.fallback;
      }

      return {
        ...command,
        displayLabel: label,
      };
    });
  }, [t]);


  /*
   * Global backend search.
   *
   * Search starts after 2 characters.
   *
   * Debounced to avoid making an API request
   * for every single keystroke.
   */
  useEffect(() => {
    if (!open) {
      return;
    }

    const normalizedQuery =
      query.trim();

    if (normalizedQuery.length < 2) {
      setSearchResults([]);
      setSearchLoading(false);
      setSearchError(false);
      return;
    }

    let cancelled = false;

    const timer = setTimeout(
      async () => {
        try {
          setSearchLoading(true);
          setSearchError(false);

          const response = await api.get(
            "/search",
            {
              params: {
                q: normalizedQuery,
              },
            }
          );

          if (cancelled) {
            return;
          }

          const results =
            buildSearchResults(
              response?.data,
              t
            );

          setSearchResults(results);
          setSelectedIndex(0);
        } catch (error) {
          if (cancelled) {
            return;
          }

          console.error(
            "Global search failed:",
            error
          );

          setSearchResults([]);
          setSearchError(true);
        } finally {
          if (!cancelled) {
            setSearchLoading(false);
          }
        }
      },
      300
    );

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query, open, t]);


  /*
   * Navigation / quick action filtering.
   *
   * When the query is empty:
   * show normal commands.
   *
   * When searching:
   * show global search results.
   *
   * We also allow commands to appear if the
   * search query matches them.
   */
  const filteredCommands = useMemo(() => {
    const normalizedQuery =
      query.trim().toLowerCase();

    if (normalizedQuery.length >= 2) {
      return searchResults;
    }

    if (!normalizedQuery) {
      return commands;
    }

    return commands.filter((command) => {
      const label =
        command.displayLabel
          ?.toLowerCase() || "";

      const fallback =
        command.fallback
          ?.toLowerCase() || "";

      const id =
        command.id
          ?.toLowerCase() || "";

      return (
        label.includes(normalizedQuery) ||
        fallback.includes(normalizedQuery) ||
        id.includes(normalizedQuery)
      );
    });
  }, [
    commands,
    query,
    searchResults,
  ]);


  /*
   * Keep selection valid.
   */
  useEffect(() => {
    if (
      selectedIndex >=
      filteredCommands.length
    ) {
      setSelectedIndex(
        Math.max(
          0,
          filteredCommands.length - 1
        )
      );
    }
  }, [
    filteredCommands.length,
    selectedIndex,
  ]);


  /*
   * Execute command/result.
   */
  const executeCommand = (
    command
  ) => {
    if (!command) {
      return;
    }

    onClose();

    navigate(
      command.path || "/"
    );
  };


  /*
   * Keyboard navigation.
   */
  const handleSearchKeyDown = (
    event
  ) => {
    if (
      event.key === "ArrowDown"
    ) {
      event.preventDefault();

      if (
        filteredCommands.length
      ) {
        setSelectedIndex(
          (current) =>
            Math.min(
              current + 1,
              filteredCommands.length -
                1
            )
        );
      }

      return;
    }


    if (
      event.key === "ArrowUp"
    ) {
      event.preventDefault();

      if (
        filteredCommands.length
      ) {
        setSelectedIndex(
          (current) =>
            Math.max(
              current - 1,
              0
            )
        );
      }

      return;
    }


    if (
      event.key === "Enter"
    ) {
      event.preventDefault();

      executeCommand(
        filteredCommands[
          selectedIndex
        ]
      );
    }
  };


  if (!open) {
    return null;
  }


  const isGlobalSearch =
    query.trim().length >= 2;


  return (
    <div
      className="fixed inset-0 z-[100] flex items-start justify-center px-4 pt-[12vh] sm:pt-[15vh]"
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
    >

      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-in fade-in duration-150"
        onClick={onClose}
      />


      {/* Palette */}
      <div className="relative w-full max-w-2xl overflow-hidden rounded-xl border border-border bg-card shadow-2xl animate-in fade-in zoom-in-95 duration-150">

        {/* Search */}
        <div className="flex items-center gap-3 border-b border-border px-4">

          {searchLoading ? (
            <Loader2 className="h-5 w-5 shrink-0 text-muted-foreground animate-spin" />
          ) : (
            <Search className="h-5 w-5 shrink-0 text-muted-foreground" />
          )}

          <input
            id="command-palette-search"
            value={query}
            onChange={(event) => {
              setQuery(
                event.target.value
              );

              setSelectedIndex(0);
            }}
            onKeyDown={
              handleSearchKeyDown
            }
            placeholder={
              t("searchAnything") ||
              "Search clients, suppliers, invoices..."
            }
            className="h-14 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            autoComplete="off"
          />

          <button
            type="button"
            onClick={onClose}
            className="flex h-7 items-center gap-1 rounded-md border border-border px-2 text-xs text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
          >
            <X className="h-3.5 w-3.5" />

            <span className="hidden sm:inline">
              Esc
            </span>
          </button>

        </div>


        {/* Results */}
        <div className="max-h-[55vh] overflow-y-auto p-2">

          {/* Loading */}
          {isGlobalSearch &&
            searchLoading &&
            searchResults.length === 0 && (
              <div className="py-12 text-center">

                <Loader2 className="mx-auto h-7 w-7 animate-spin text-muted-foreground" />

                <div className="mt-3 text-sm text-muted-foreground">
                  {t("searching") ||
                    "Searching..."}
                </div>

              </div>
            )}


          {/* Error */}
          {isGlobalSearch &&
            !searchLoading &&
            searchError && (
              <div className="py-12 text-center">

                <Search className="mx-auto h-8 w-8 text-muted-foreground/40" />

                <div className="mt-3 text-sm font-medium">
                  {t("searchFailed") ||
                    "Search failed"}
                </div>

                <div className="mt-1 text-xs text-muted-foreground">
                  {t("tryAgain") ||
                    "Please try again."}
                </div>

              </div>
            )}


          {/* No search results */}
          {isGlobalSearch &&
            !searchLoading &&
            !searchError &&
            searchResults.length === 0 && (
              <div className="py-12 text-center">

                <Search className="mx-auto h-8 w-8 text-muted-foreground/40" />

                <div className="mt-3 text-sm font-medium">
                  {t("noResults") ||
                    "No results found"}
                </div>

                <div className="mt-1 text-xs text-muted-foreground">
                  {t("tryAnotherSearch") ||
                    "Try another search."}
                </div>

              </div>
            )}


          {/* Search results */}
          {isGlobalSearch &&
            searchResults.length > 0 && (
              <div className="space-y-1">

                {searchResults.map(
                  (
                    result,
                    index
                  ) => {
                    const Icon =
                      result.icon;

                    const selected =
                      index ===
                      selectedIndex;

                    return (
                      <button
                        key={
                          result.id
                        }
                        type="button"
                        onMouseEnter={() =>
                          setSelectedIndex(
                            index
                          )
                        }
                        onClick={() =>
                          executeCommand(
                            result
                          )
                        }
                        className={`group flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left transition-colors ${
                          selected
                            ? "bg-accent text-accent-foreground"
                            : "text-foreground hover:bg-accent/60"
                        }`}
                      >

                        <div
                          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-md border ${
                            selected
                              ? "border-border bg-background/50"
                              : "border-border bg-background"
                          }`}
                        >
                          <Icon className="h-4 w-4" />
                        </div>


                        <div className="min-w-0 flex-1">

                          <div className="truncate text-sm font-medium">
                            {result.label}
                          </div>

                          <div className="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground">

                            <span>
                              {result.groupLabel}
                            </span>

                            {result.subtitle && (
                              <>
                                <span>
                                  •
                                </span>

                                <span className="truncate">
                                  {
                                    result.subtitle
                                  }
                                </span>
                              </>
                            )}

                          </div>

                        </div>


                        <ArrowRight
                          className={`h-4 w-4 shrink-0 transition-transform ${
                            selected
                              ? "translate-x-0 opacity-100"
                              : "-translate-x-1 opacity-0"
                          }`}
                        />

                      </button>
                    );
                  }
                )}

              </div>
            )}


          {/* Normal commands */}
          {!isGlobalSearch &&
            !searchLoading && (
              <>
                {filteredCommands.length ===
                0 ? (

                  <div className="py-12 text-center">

                    <Search className="mx-auto h-8 w-8 text-muted-foreground/40" />

                    <div className="mt-3 text-sm font-medium">
                      {t("noResults") ||
                        "No results found"}
                    </div>

                    <div className="mt-1 text-xs text-muted-foreground">
                      {t(
                        "tryAnotherSearch"
                      ) ||
                        "Try another search."}
                    </div>

                  </div>

                ) : (

                  <div className="space-y-1">

                    {filteredCommands.map(
                      (
                        command,
                        index
                      ) => {
                        const Icon =
                          command.icon;

                        const selected =
                          index ===
                          selectedIndex;

                        return (
                          <button
                            key={
                              command.id
                            }
                            type="button"
                            onMouseEnter={() =>
                              setSelectedIndex(
                                index
                              )
                            }
                            onClick={() =>
                              executeCommand(
                                command
                              )
                            }
                            className={`group flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left transition-colors ${
                              selected
                                ? "bg-accent text-accent-foreground"
                                : "text-foreground hover:bg-accent/60"
                            }`}
                          >

                            <div
                              className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-md border ${
                                selected
                                  ? "border-border bg-background/50"
                                  : "border-border bg-background"
                              }`}
                            >
                              <Icon className="h-4 w-4" />
                            </div>


                            <div className="min-w-0 flex-1">

                              <div className="truncate text-sm font-medium">
                                {
                                  command.displayLabel
                                }
                              </div>

                              <div className="mt-0.5 text-xs text-muted-foreground">
                                {command.type ===
                                "action"
                                  ? t(
                                      "quickAction"
                                    ) ||
                                    "Quick action"
                                  : t(
                                      "navigation"
                                    ) ||
                                    "Navigation"}
                              </div>

                            </div>


                            <ArrowRight
                              className={`h-4 w-4 shrink-0 transition-transform ${
                                selected
                                  ? "translate-x-0 opacity-100"
                                  : "-translate-x-1 opacity-0"
                              }`}
                            />

                          </button>
                        );
                      }
                    )}

                  </div>
                )}

              </>
            )}

        </div>


        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border bg-muted/30 px-4 py-2.5">

          <div className="text-[11px] text-muted-foreground">
            {isGlobalSearch
              ? (
                  t("globalSearch") ||
                  "Global Search"
                )
              : (
                  t("commandPaletteHint") ||
                  "Navigate faster with Command Palette"
                )}
          </div>


          <div className="flex items-center gap-2 text-[10px] text-muted-foreground">

            <span className="rounded border border-border px-1.5 py-0.5">
              ↑↓
            </span>

            <span>
              {t("navigate") ||
                "Navigate"}
            </span>

            <span className="rounded border border-border px-1.5 py-0.5">
              Enter
            </span>

            <span>
              {t("open") ||
                "Open"}
            </span>

          </div>

        </div>

      </div>

    </div>
  );
}