import { useMemo } from "react";
import { useTree } from "@headless-tree/react";
import { searchFeature, syncDataLoaderFeature } from "@headless-tree/core";
import { Link } from "react-router-dom";

const treeData = {
  root: {
    name: "Workspace",
    type: "folder",
    children: ["projects", "documents", "archives"],
  },
  projects: {
    name: "Projects",
    type: "folder",
    children: ["project-a", "project-b"],
  },
  "project-a": {
    name: "Project A",
    type: "folder",
    children: ["project-a-design", "project-a-code"],
  },
  "project-a-design": {
    name: "Design",
    type: "folder",
    children: ["project-a-design-assets", "project-a-design-docs"],
  },
  "project-a-design-assets": {
    name: "Assets",
    type: "folder",
    children: ["project-a-design-assets-logo"],
  },
  "project-a-design-assets-logo": {
    name: "Logo.png",
    type: "file",
    children: [],
  },
  "project-a-design-docs": {
    name: "Docs",
    type: "folder",
    children: ["project-a-design-docs-specs"],
  },
  "project-a-design-docs-specs": {
    name: "Specs.pdf",
    type: "file",
    children: [],
  },
  "project-a-code": {
    name: "Code",
    type: "folder",
    children: ["project-a-code-src", "project-a-code-tests"],
  },
  "project-a-code-src": {
    name: "src",
    type: "folder",
    children: ["project-a-code-src-index", "project-a-code-src-utils"],
  },
  "project-a-code-src-index": {
    name: "index.jsx",
    type: "file",
    children: [],
  },
  "project-a-code-src-utils": {
    name: "utils.js",
    type: "file",
    children: [],
  },
  "project-a-code-tests": {
    name: "tests",
    type: "folder",
    children: ["project-a-code-tests-app"],
  },
  "project-a-code-tests-app": {
    name: "app.test.js",
    type: "file",
    children: [],
  },
  "project-b": {
    name: "Project B",
    type: "folder",
    children: ["project-b-docs", "project-b-assets"],
  },
  "project-b-docs": {
    name: "Documentation",
    type: "folder",
    children: ["project-b-docs-manual"],
  },
  "project-b-docs-manual": {
    name: "Manual.docx",
    type: "file",
    children: [],
  },
  "project-b-assets": {
    name: "Assets",
    type: "folder",
    children: ["project-b-assets-mockups"],
  },
  "project-b-assets-mockups": {
    name: "Mockups.sketch",
    type: "file",
    children: [],
  },
  documents: {
    name: "Documents",
    type: "folder",
    children: ["meeting-notes", "roadmap"],
  },
  "meeting-notes": {
    name: "Meeting Notes",
    type: "folder",
    children: ["meeting-notes-2026"],
  },
  "meeting-notes-2026": {
    name: "2026-04-18.md",
    type: "file",
    children: [],
  },
  roadmap: {
    name: "Roadmap",
    type: "file",
    children: [],
  },
  archives: {
    name: "Archives",
    type: "folder",
    children: ["old-projects"],
  },
  "old-projects": {
    name: "Old Projects",
    type: "folder",
    children: ["old-projects-archive"],
  },
  "old-projects-archive": {
    name: "archive.zip",
    type: "file",
    children: [],
  },
};

const getTreeItemsWithAncestors = (items, matchingIds) => {
  if (!matchingIds.size) {
    return items;
  }

  const visibleIds = new Set();

  items.forEach((item, index) => {
    if (matchingIds.has(item.getId())) {
      visibleIds.add(item.getId());
      let currentLevel = item.getItemMeta().level;

      for (let i = index - 1; i >= 0; i -= 1) {
        const candidate = items[i];
        const candidateLevel = candidate.getItemMeta().level;

        if (candidateLevel < currentLevel) {
          visibleIds.add(candidate.getId());
          currentLevel = candidateLevel;
        }

        if (currentLevel === 0) {
          break;
        }
      }
    }
  });

  return items.filter((item) => visibleIds.has(item.getId()));
};

export default function TreePage() {
  const tree = useTree({
    rootItemId: "root",
    getItemName: (item) => item.getItemData().name,
    isItemFolder: (item) => item.getItemData().type === "folder",
    dataLoader: {
      getItem: (itemId) => treeData[itemId],
      getChildren: (itemId) => treeData[itemId]?.children ?? [],
    },
    initialState: {
      expandedItems: [
        "root",
        "projects",
        "project-a",
        "project-a-design",
        "project-a-code",
        "project-a-code-src",
        "project-b",
      ],
    },
    indent: 18,
    features: [syncDataLoaderFeature, searchFeature],
  });

  const items = tree.getItems();
  const searchValue = tree.getSearchValue();
  const matchingItems = tree.getSearchMatchingItems();
  const matchedIds = new Set(matchingItems.map((item) => item.getId()));

  const visibleItems = useMemo(
    () => getTreeItemsWithAncestors(items, matchedIds),
    [items, matchedIds],
  );

  const noSearchResults = searchValue && matchingItems.length === 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-3xl border border-[var(--color-border)] bg-[var(--color-card)] p-5 shadow-sm">
        <div>
          <h2 className="text-xl font-semibold text-white">Test Tree</h2>
          <p className="text-sm text-gray-400">
            Browse a multi-level folder structure and search for matching nodes.
          </p>
        </div>
        <Link
          to="/"
          className="rounded-full border border-blue-500 bg-blue-500/10 px-4 py-2 text-sm text-blue-200 transition hover:bg-blue-500/20"
        >
          Back to dashboard
        </Link>
      </div>

      <div className="rounded-3xl border border-[var(--color-border)] bg-[var(--color-card)] p-5 shadow-sm">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <label htmlFor="tree-search" className="text-sm font-medium text-gray-300">
              Search tree
            </label>
            <p className="text-xs text-gray-500">
              Type a name fragment to filter the tree and show only matching nodes.
            </p>
          </div>
          <input
            id="tree-search"
            type="search"
            autoComplete="off"
            spellCheck="false"
            {...tree.getSearchInputElementProps()}
            className="w-full rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2 text-sm text-white outline-none transition focus:border-blue-400 sm:w-auto"
            placeholder="Search folders, files, or names..."
          />
        </div>

        {noSearchResults ? (
          <div className="rounded-2xl border border-yellow-500/20 bg-yellow-500/10 px-4 py-5 text-sm text-yellow-100">
            No matching tree nodes found for “{searchValue}”. Try a different search term.
          </div>
        ) : (
          <div {...tree.getContainerProps()} className="space-y-1">
            {visibleItems.map((item) => {
              const meta = item.getItemMeta();
              const isMatch = item.isMatchingSearch();
              const isFolder = item.isFolder();

              return (
                <div
                  key={item.getId()}
                  {...item.getProps()}
                  className={`flex items-center gap-3 rounded-2xl px-3 py-2 text-sm transition ${
                    isMatch
                      ? "border border-blue-500/30 bg-blue-500/10 text-white"
                      : "border border-transparent bg-[var(--color-surface)]/60 text-gray-100 hover:border-[var(--color-border)] hover:bg-[var(--color-surface)]"
                  }`}
                  style={{ paddingLeft: `${meta.level * 18}px` }}
                >
                  <span className="text-base">
                    {isFolder ? "📁" : "📄"}
                  </span>
                  <span className="truncate">{item.getItemName()}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
