import { useMemo, useState, useCallback, useRef, useEffect } from "react";
import { useTree } from "@headless-tree/react";
import { searchFeature, syncDataLoaderFeature } from "@headless-tree/core";
import { Link } from "react-router-dom";

// Debounce hook for search
function useDebounce(value, delay) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

// Generate large mock dataset (simulating 4MB of data)
const generateLargeTreeData = (size = 10000) => {
  const data = {};
  const rootChildren = [];

  // Create root
  data.root = {
    name: "Workspace",
    type: "folder",
    children: rootChildren,
  };

  // Generate large hierarchical structure
  for (let i = 0; i < size; i++) {
    const folderId = `folder-${i}`;
    const folderChildren = [];

    // Each folder has 2-4 subfolders (reduced for performance)
    const subFolderCount = Math.floor(Math.random() * 3) + 2;
    for (let j = 0; j < subFolderCount; j++) {
      const subFolderId = `${folderId}-sub-${j}`;
      const subFolderChildren = [];

      // Each subfolder has 1-3 files (reduced for performance)
      const fileCount = Math.floor(Math.random() * 3) + 1;
      for (let k = 0; k < fileCount; k++) {
        const fileId = `${subFolderId}-file-${k}`;
        data[fileId] = {
          name: `file-${k}.js`,
          type: "file",
          children: [],
        };
        subFolderChildren.push(fileId);
      }

      data[subFolderId] = {
        name: `Subfolder ${j}`,
        type: "folder",
        children: subFolderChildren,
      };
      folderChildren.push(subFolderId);
    }

    data[folderId] = {
      name: `Folder ${i}`,
      type: "folder",
      children: folderChildren,
    };
    rootChildren.push(folderId);
  }

  return data;
};

// Lazy loading hook for large datasets
function useLazyTreeData(initialSize = 100, chunkSize = 50) {
  // Generate full dataset once and store it
  const fullDataset = useMemo(() => generateLargeTreeData(1000), []);

  const [treeData, setTreeData] = useState(() => {
    // Start with a small dataset
    const initialData = {};
    const rootChildren = [];

    // Create root
    initialData.root = {
      name: "Workspace",
      type: "folder",
      children: rootChildren,
    };

    // Add initial items from full dataset
    for (let i = 0; i < Math.min(initialSize, 1000); i++) {
      const folderId = `folder-${i}`;
      if (fullDataset[folderId]) {
        initialData[folderId] = fullDataset[folderId];
        rootChildren.push(folderId);
      }
    }

    return initialData;
  });

  return { treeData };
}

const getTreeItemsWithAncestors = (items, matchingIds) => {
  if (!items || !Array.isArray(items)) return [];
  if (!matchingIds || !matchingIds.size) {
    return items;
  }

  const visibleIds = new Set();

  items.forEach((item, index) => {
    if (!item) return;
    if (matchingIds.has(item.getId())) {
      visibleIds.add(item.getId());
      let currentLevel = item.getItemMeta()?.level ?? 0;

      for (let i = index - 1; i >= 0; i -= 1) {
        const candidate = items[i];
        if (!candidate) continue;
        const candidateLevel = candidate.getItemMeta()?.level ?? 0;

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

  return items.filter((item) => item && visibleIds.has(item.getId()));
};

export default function TreePage() {
  const { treeData } = useLazyTreeData();
  const [searchQuery, setSearchQuery] = useState("");
  const debouncedSearchQuery = useDebounce(searchQuery, 300);
  const [expandedItems, setExpandedItems] = useState([]);

  const tree = useTree({
    rootItemId: "root",
    getItemName: (item) => item.getItemData().name,
    isItemFolder: (item) => item.getItemData().type === "folder",
    dataLoader: {
      getItem: (itemId) => treeData[itemId],
      getChildren: (itemId) => treeData[itemId]?.children ?? [],
    },
    initialState: {
      expandedItems: [], // Start with no items expanded
    },
    indent: 18,
    features: [syncDataLoaderFeature, searchFeature],
  });

  // Expansion state is managed purely through React state and doesn't need tree sync

  const items = tree.getItems();
  const searchValue = tree.getSearchValue();
  const matchingItems = tree.getSearchMatchingItems();
  const matchedIds = new Set(matchingItems?.map((item) => item?.getId()) || []);

  const visibleItems = useMemo(
    () => {
      const treeItems = items || [];
      const searchFiltered = getTreeItemsWithAncestors(treeItems, matchedIds);
      
      // Filter based on expansion state - only show items whose parents are expanded
      return searchFiltered.filter((item) => {
        const path = item.getId().split('-');
        // Root is always visible
        if (path.length <= 1) return true;
        
        // An item is visible if its parent folder is expanded or if we're searching and its ancestor is in expandedItems
        // For nested items, check if each parent level is expanded
        let parentId = '';
        for (let i = 0; i < path.length - 1; i++) {
          if (i === 0) {
            parentId = path[i];
          } else {
            parentId = path.slice(0, i + 1).join('-');
          }
          
          // If parent is not expanded (unless we're at root), filter it out
          if (parentId !== 'root' && !expandedItems.includes(parentId)) {
            return false;
          }
        }
        return true;
      });
    },
    [items, matchedIds, expandedItems], // Re-calculate when expansion changes
  );

  // Ensure visibleItems is always an array and filter out any invalid items
  const safeVisibleItems = useMemo(() => {
    if (!Array.isArray(visibleItems)) return [];
    return visibleItems.filter((item) =>
      item &&
      typeof item.getId === 'function' &&
      typeof item.getItemMeta === 'function' &&
      typeof item.getItemName === 'function'
    );
  }, [visibleItems]);

  // Check if tree data is ready
  const isTreeReady = treeData && treeData.root && safeVisibleItems.length > 0;

  // Update search when debounced query changes
  useEffect(() => {
    if (!isTreeReady) return;
    
    if (debouncedSearchQuery) {
      tree.openSearch();
      tree.setSearch(debouncedSearchQuery);
    } else {
      tree.closeSearch();
    }
  }, [debouncedSearchQuery, tree, isTreeReady]);

  // Expand visible items when searching (limit to prevent performance issues)
  useEffect(() => {
    if (debouncedSearchQuery && safeVisibleItems.length > 0) {
      // Only expand folders that contain direct matches, not all ancestors
      // This prevents expanding thousands of folders at once
      const foldersWithMatches = new Set();
      matchingItems.forEach(match => {
        // Find the immediate parent folder of each match
        const path = match.getId().split('-');
        if (path.length >= 2) {
          // For files like "folder-1-sub-2-file-3", the parent is "folder-1-sub-2"
          const parentPath = path.slice(0, -2).join('-'); // Remove "-file-3"
          if (parentPath) foldersWithMatches.add(parentPath);
        }
      });

      setExpandedItems(Array.from(foldersWithMatches));
    } else if (!debouncedSearchQuery) {
      // Collapse all when not searching
      setExpandedItems([]);
    }
  }, [debouncedSearchQuery, safeVisibleItems, matchingItems]);

  const noSearchResults = searchValue && matchingItems.length === 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-3xl border border-[var(--color-border)] bg-[var(--color-card)] p-5 shadow-sm">
        <div>
          <h2 className="text-xl font-semibold text-white">Large Tree Demo</h2>
          <p className="text-sm text-gray-400">
            Handling 4MB+ of tree data with virtualization, lazy loading, and debounced search.
          </p>
          <div className="mt-2 text-xs text-gray-500">
            Loaded: {Object.keys(treeData).length - 1} items (simplified view)
          </div>
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
              Search tree (debounced)
            </label>
            <p className="text-xs text-gray-500">
              Type to search through {safeVisibleItems.length.toLocaleString()} items. Search is debounced for performance.
            </p>
          </div>
          <input
            id="tree-search"
            type="search"
            autoComplete="off"
            spellCheck="false"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2 text-sm text-white outline-none transition focus:border-blue-400 sm:w-auto"
            placeholder="Search folders, files, or names..."
          />
        </div>

        {noSearchResults ? (
          <div className="rounded-2xl border border-yellow-500/20 bg-yellow-500/10 px-4 py-5 text-sm text-yellow-100">
            No matching tree nodes found for "{searchValue}". Try a different search term.
          </div>
        ) : !isTreeReady ? (
          <div className="rounded-2xl border border-gray-500/20 bg-gray-500/10 px-4 py-5 text-sm text-gray-100">
            Loading tree data...
          </div>
        ) : (
          <div className="h-96 border border-[var(--color-border)] rounded-2xl overflow-hidden">
            <div className="h-full overflow-auto scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800">
              {safeVisibleItems.map((item, index) => {
                if (!item || typeof item.getItemMeta !== 'function' || typeof item.getItemName !== 'function') {
                  return (
                    <div key={index} className="px-3 py-2 text-sm text-gray-500">
                      Loading...
                    </div>
                  );
                }

                const meta = item.getItemMeta();
                const isMatch = item.isMatchingSearch && typeof item.isMatchingSearch === 'function' ? item.isMatchingSearch() : false;
                const isFolder = item.isFolder && typeof item.isFolder === 'function' ? item.isFolder() : false;
                const isExpanded = expandedItems.includes(item.getId());
                const itemName = item.getItemName();

                const handleClick = () => {
                  if (isFolder) {
                    if (isExpanded) {
                      // Collapse
                      setExpandedItems(expandedItems.filter(id => id !== item.getId()));
                    } else {
                      // Expand
                      setExpandedItems([...expandedItems, item.getId()]);
                    }
                  }
                };

                return (
                  <div
                    key={item.getId()}
                    onClick={handleClick}
                    className={`flex items-center gap-3 px-3 py-2 text-sm transition cursor-pointer ${
                      isMatch
                        ? "border border-blue-500/30 bg-blue-500/10 text-white"
                        : "border border-transparent bg-[var(--color-surface)]/60 text-gray-100 hover:border-[var(--color-border)] hover:bg-[var(--color-surface)]"
                    }`}
                  >
                    <div
                      className="flex-shrink-0"
                      style={{ width: `${(meta?.level ?? 0) * 18}px` }}
                    />
                    <span className="text-base">
                      {isFolder ? (isExpanded ? "📂" : "📁") : "📄"}
                    </span>
                    <span className="truncate">{itemName || 'Unknown'}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}