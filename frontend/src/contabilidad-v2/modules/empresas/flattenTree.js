/* ── Helper compartido: aplanar árbol de entidades CT a lista ──
   Antes duplicado idéntico en CompanySelector.jsx y DashboardPanel.jsx. */
export function flattenTree(tree, level = 0) {
  const result = [];
  for (const node of (tree || [])) {
    result.push({
      id: node.id,
      name: node.name,
      type: node.type || 'EMPRESA',
      parent_id: node.parent_id,
      industry: node.industry || 'ESTANDAR',
      portfolio_id: node.portfolio_id,
      status: node.status || 'AL DIA',
      level,
    });
    if (node.children?.length) {
      result.push(...flattenTree(node.children, level + 1));
    }
  }
  return result;
}

export default flattenTree;
