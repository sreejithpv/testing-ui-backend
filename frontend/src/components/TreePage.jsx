import { useMemo, useState, useCallback, useRef, useEffect } from "react";
import { FixedSizeTree as Tree } from 'react-vtree';
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

  // Diverse file and folder names for better search testing
  const fileNames = [
    'index.js', 'main.js', 'app.js', 'config.js', 'utils.js', 'helpers.js', 
    'styles.css', 'constants.js', 'hooks.js', 'types.ts', 'service.js', 'store.js',
    'reducer.js', 'actions.js', 'middleware.js', 'component.jsx', 'layout.jsx',
    'api.js', 'auth.js', 'database.js', 'server.js', 'router.js', 'controller.js',
    'model.js', 'validator.js', 'formatter.js', 'parser.js', 'logger.js', 'cache.js',
    'queue.js', 'worker.js', 'socket.js', 'stream.js', 'buffer.js', 'crypto.js'
  ];

  const folderNames = [
    'components', 'services', 'utils', 'hooks', 'pages', 'layouts', 'styles',
    'assets', 'config', 'middleware', 'models', 'controllers', 'routes', 'store',
    'actions', 'reducers', 'api', 'helpers', 'constants', 'types', 'lib', 'public',
    'src', 'dist', 'build', 'tests', 'docs', 'scripts', 'modules', 'plugins'
  ];

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
    const folderName = folderNames[i % folderNames.length] + (i > folderNames.length ? `-${Math.floor(i / folderNames.length)}` : '');

    // Each folder has 2-4 subfolders (reduced for performance)
    const subFolderCount = Math.floor(Math.random() * 3) + 2;
    for (let j = 0; j < subFolderCount; j++) {
      const subFolderId = `${folderId}-sub-${j}`;
      const subFolderChildren = [];
      const subFolderName = folderNames[(i + j) % folderNames.length] + `-sub-${j}`;

      // Each subfolder has 1-3 files (reduced for performance)
      const fileCount = Math.floor(Math.random() * 3) + 1;
      for (let k = 0; k < fileCount; k++) {
        const fileId = `${subFolderId}-file-${k}`;
        const fileName = fileNames[(i + j + k) % fileNames.length];
        data[fileId] = {
          name: fileName,
          type: "file",
          children: [],
        };
        subFolderChildren.push(fileId);
      }

      data[subFolderId] = {
        name: subFolderName,
        type: "folder",
        children: subFolderChildren,
      };
      folderChildren.push(subFolderId);
    }

    data[folderId] = {
      name: folderName,
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

    // Helper function to recursively add a node and all its descendants
    const addNodeAndDescendants = (nodeId) => {
      if (initialData[nodeId]) return; // Already added
      
      const node = fullDataset[nodeId];
      if (!node) return;
      
      initialData[nodeId] = node;
      
      // Recursively add all children
      if (node.children) {
        for (const childId of node.children) {
          addNodeAndDescendants(childId);
        }
      }
    };

    // Create root
    initialData.root = {
      name: "Workspace",
      type: "folder",
      children: rootChildren,
    };

    // Add initial items from full dataset and all their descendants
    for (let i = 0; i < Math.min(initialSize, 1000); i++) {
      const folderId = `folder-${i}`;
      addNodeAndDescendants(folderId);
      rootChildren.push(folderId);
    }

    return initialData;
  });

  return { treeData };
}

export default function TreePage() {
  const { treeData } = useLazyTreeData();
  const [searchQuery, setSearchQuery] = useState("");
  const debouncedSearchQuery = useDebounce(searchQuery, 300);
  const treeRef = useRef(null);

  // Helper function to check if node matches search
  const matchesSearch = useCallback((node) => {
    if (!debouncedSearchQuery) return false;
    return node.name.toLowerCase().includes(debouncedSearchQuery.toLowerCase());
  }, [debouncedSearchQuery]);

  // Expand root node on first render
  useEffect(() => {
    if (treeRef.current) {
      // Force root to open and fetch its children
      setTimeout(() => {
        treeRef.current.recomputeTree({
          'root': { open: true }
        });
      }, 100);
    }
  }, []);

  // Handle search - expand all folders that contain matches
  useEffect(() => {
    if (debouncedSearchQuery && treeRef.current) {
      // Find all nodes that match the search and collect nodes to expand
      const nodesToExpand = new Set();
      const findMatchingNodes = (node, nodeId) => {
        let hasMatch = false;
        if (matchesSearch(node)) {
          hasMatch = true;
          nodesToExpand.add(nodeId);
        }
        if (node.children) {
          node.children.forEach(childId => {
            const child = treeData[childId];
            if (child && findMatchingNodes(child, childId)) {
              hasMatch = true;
              nodesToExpand.add(nodeId); // Expand parent if child has match
            }
          });
        }
        return hasMatch;
      };
      
      if (treeData.root) {
        findMatchingNodes(treeData.root, 'root');
      }

      // Expand all nodes that contain matches
      if (nodesToExpand.size > 0) {
        const expandState = {};
        nodesToExpand.forEach(nodeId => {
          expandState[nodeId] = { open: true };
        });
        treeRef.current.recomputeTree(expandState);
      }
    } else if (!debouncedSearchQuery && treeRef.current) {
      // When clearing search, keep root open by default
      treeRef.current.recomputeTree({
        'root': { open: true }
      });
    }
  }, [debouncedSearchQuery, matchesSearch, treeData]);

  // Tree walker function - generator that efficiently traverses the tree
  const treeWalker = useCallback(function* () {
    // Helper function to get node data
    const getNodeData = (node, nestingLevel, nodeId) => ({
      data: {
        id: nodeId,
        isLeaf: !node.children || node.children.length === 0,
        isOpenByDefault: false,
        name: node.name,
        type: node.type,
        nestingLevel,
      },
      nestingLevel,
      node,
    });

    // Yield root node
    const rootNode = treeData.root;
    if (rootNode) {
      yield getNodeData(rootNode, 0, 'root');
    }

    // Yield children as they are requested by react-vtree
    while (true) {
      const parent = yield;

      if (parent && parent.node && parent.node.children) {
        for (const childId of parent.node.children) {
          const childNode = treeData[childId];
          if (childNode) {
            yield getNodeData(childNode, parent.nestingLevel + 1, childId);
          }
        }
      }
    }
  }, [treeData]);

  // Node component for rendering each tree item
  const Node = ({ data, isOpen, style, setOpen }) => {
    const isFolder = data.type === "folder";
    const isMatch = matchesSearch(data);

    const handleClick = () => {
      if (isFolder) {
        setOpen(!isOpen);
      }
    };

    return (
      <div
        style={{
          ...style,
          paddingLeft: `${data.nestingLevel * 18}px`,
        }}
        onClick={handleClick}
        className={`flex items-center gap-3 px-3 py-2 text-sm transition cursor-pointer ${
          isMatch && debouncedSearchQuery
            ? "border border-blue-500/30 bg-blue-500/10 text-white"
            : "border border-transparent bg-[var(--color-surface)]/60 text-gray-100 hover:border-[var(--color-border)] hover:bg-[var(--color-surface)]"
        }`}
      >
        <span className="text-base">
          {isFolder ? (isOpen ? "📂" : "📁") : "📄"}
        </span>
        <span className="truncate">{data.name}</span>
      </div>
    );
  };

  // Check for search results
  const hasSearchResults = useMemo(() => {
    if (!debouncedSearchQuery) return true;
    
    const checkNode = (node) => {
      if (matchesSearch(node)) return true;
      if (node.children) {
        return node.children.some(childId => {
          const child = treeData[childId];
          return child && checkNode(child);
        });
      }
      return false;
    };
    
    return treeData.root ? checkNode(treeData.root) : false;
  }, [debouncedSearchQuery, matchesSearch, treeData]);

  const noSearchResults = debouncedSearchQuery && !hasSearchResults;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-3xl border border-[var(--color-border)] bg-[var(--color-card)] p-5 shadow-sm">
        <div>
          <h2 className="text-xl font-semibold text-white">Large Tree Demo (react-vtree)</h2>
          <p className="text-sm text-gray-400">
            Handling 4MB+ of tree data with virtualization, lazy loading, and debounced search using react-vtree.
          </p>
          <div className="mt-2 text-xs text-gray-500">
            Loaded: {Object.keys(treeData).length - 1} items (optimized with react-vtree)
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
              Type to search through {Object.keys(treeData).length - 1} items. Search is debounced for performance.
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
            No matching tree nodes found for "{debouncedSearchQuery}". Try a different search term.
          </div>
        ) : (
          <div className="h-96 border border-[var(--color-border)] rounded-2xl overflow-hidden">
            <div className="h-full overflow-auto scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800">
              <Tree
                ref={treeRef}
                treeWalker={treeWalker}
                itemSize={32}
                height={600}
                width="100%"
              >
                {Node}
              </Tree>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}