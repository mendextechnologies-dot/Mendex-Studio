import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import {
  DollarSign,
  TrendingDown,
  Layers,
  Download,
  Printer,
  RefreshCw,
  Search,
  Filter,
  BarChart2,
  Package,
  Clock,
  ShieldCheck,
  AlertCircle,
  FileSpreadsheet,
  FileText,
  X,
  ExternalLink,
} from 'lucide-react';

interface BOMPricingScheduleCardProps {
  revisionId: string;
  projectCode: string;
  projectName: string;
}

export const BOMPricingScheduleCard: React.FC<BOMPricingScheduleCardProps> = ({
  revisionId,
  projectCode,
  projectName,
}) => {
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pricingData, setPricingData] = useState<any | null>(null);

  // Active volume tier: 'tier_1' | 'tier_25' | 'tier_100' | 'tier_1000'
  const [selectedTier, setSelectedTier] = useState<'tier_1' | 'tier_25' | 'tier_100' | 'tier_1000'>('tier_1000');

  // Filter & Search
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('ALL');

  // Preview Modal for HTML Report
  const [previewModalOpen, setPreviewModalOpen] = useState(false);

  const fetchPricing = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getBOMPricing(revisionId);
      if (res && res.success) {
        setPricingData(res);
      }
    } catch (err: any) {
      try {
        const genRes = await api.generateBOMPricing(revisionId);
        if (genRes && genRes.success) {
          setPricingData(genRes);
        }
      } catch (genErr: any) {
        setError(genErr.message || String(genErr));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    setError(null);
    try {
      const res = await api.generateBOMPricing(revisionId);
      if (res && res.success) {
        setPricingData(res);
      }
    } catch (err: any) {
      setError(err.message || String(err));
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchPricing();
  }, [revisionId]);

  const handleDownloadCsv = () => {
    if (!pricingData?.items) return;
    const items = pricingData.items;
    const header = [
      'Item',
      'Designator',
      'Qty',
      'Description',
      'Manufacturer',
      'MPN',
      'Package',
      'Category',
      'Lifecycle',
      'Distributor',
      'Lead_Time',
      'Sourcing_Risk',
      'Unit_Price_1',
      'Ext_Price_1',
      'Unit_Price_25',
      'Ext_Price_25',
      'Unit_Price_100',
      'Ext_Price_100',
      'Unit_Price_1000',
      'Ext_Price_1000',
    ];
    const rows = items.map((it: any) => [
      it.item_num,
      it.designator,
      it.quantity,
      `"${(it.description || '').replace(/"/g, '""')}"`,
      `"${(it.manufacturer || '').replace(/"/g, '""')}"`,
      it.mpn,
      it.package,
      it.category,
      it.lifecycle,
      it.distributor,
      it.lead_time_weeks,
      it.sourcing_risk,
      it.pricing_tiers.tier_1.unit_price,
      it.pricing_tiers.tier_1.ext_price,
      it.pricing_tiers.tier_25.unit_price,
      it.pricing_tiers.tier_25.ext_price,
      it.pricing_tiers.tier_100.unit_price,
      it.pricing_tiers.tier_100.ext_price,
      it.pricing_tiers.tier_1000.unit_price,
      it.pricing_tiers.tier_1000.ext_price,
    ]);
    const csvContent = [header.join(','), ...rows.map((r: any[]) => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `procurement_bom_${projectCode}_${pricingData.revision_id?.slice(0, 8)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleOpenPrintableHtml = () => {
    if (pricingData?.html_path) {
      setPreviewModalOpen(true);
    }
  };

  const summary = pricingData?.summary || {};
  const items: any[] = pricingData?.items || [];
  const topDrivers: any[] = pricingData?.top_cost_drivers || [];
  const categories: any[] = pricingData?.category_breakdown || [];

  const tierQtyMap = {
    tier_1: 1,
    tier_25: 25,
    tier_100: 100,
    tier_1000: 1000,
  };

  // Filter items
  const filteredItems = items.filter((it) => {
    const matchesSearch =
      searchQuery === '' ||
      it.designator?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      it.mpn?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      it.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      it.manufacturer?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = categoryFilter === 'ALL' || it.category === categoryFilter;
    return matchesSearch && matchesCategory;
  });

  const uniqueCategories = ['ALL', ...Array.from(new Set(items.map((it) => it.category)))];

  return (
    <div
      style={{
        background: '#ffffff',
        border: '1px solid #cbd5e1',
        borderRadius: '8px',
        overflow: 'hidden',
        boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
      }}
    >
      {/* 1. Header Bar */}
      <div
        style={{
          padding: '16px 20px',
          background: 'linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%)',
          borderBottom: '1px solid #cbd5e1',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '8px',
              background: '#ecfdf5',
              color: '#059669',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <DollarSign size={22} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#0f172a', margin: 0 }}>
                Production Bill of Materials (BOM) Cost Rollup & Sourcing Schedule
              </h3>
              <span
                style={{
                  fontSize: '11px',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  background: '#dcfce7',
                  color: '#166534',
                  fontWeight: 700,
                  border: '1px solid #bbf7d0',
                }}
              >
                G05 Purchasing Intelligence
              </span>
            </div>
            <p style={{ fontSize: '11px', color: '#64748b', margin: '3px 0 0 0' }}>
              Volume tiered pricing breaks (1, 25, 100, 1000 units), distributor intelligence, Pareto cost driver analysis, and lead times.
            </p>
          </div>
        </div>

        {/* Header Action Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <button
            onClick={handleRefresh}
            disabled={refreshing || loading}
            className="btn btn-secondary"
            style={{ fontSize: '11px', padding: '5px 10px', display: 'flex', alignItems: 'center', gap: '5px' }}
            title="Recalculate pricing models"
          >
            <RefreshCw size={12} className={refreshing ? 'spin' : ''} />
            <span>{refreshing ? 'Recalculating…' : 'Recalculate'}</span>
          </button>

          <button
            onClick={handleDownloadCsv}
            disabled={!pricingData}
            className="btn btn-primary"
            style={{ fontSize: '11px', padding: '5px 12px', display: 'flex', alignItems: 'center', gap: '5px' }}
            title="Download complete procurement CSV"
          >
            <Download size={12} />
            <span>Download CSV</span>
          </button>

          <button
            onClick={handleOpenPrintableHtml}
            disabled={!pricingData}
            className="btn btn-secondary"
            style={{ fontSize: '11px', padding: '5px 10px', display: 'flex', alignItems: 'center', gap: '5px' }}
            title="View printable procurement report"
          >
            <Printer size={12} />
            <span>Print Report</span>
          </button>
        </div>
      </div>

      {/* 2. Error Message */}
      {error && (
        <div style={{ padding: '10px 16px', background: '#fef2f2', borderBottom: '1px solid #fecaca', color: '#b91c1c', fontSize: '12px' }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* 3. Executive Volume Cost KPI Cards */}
      <div style={{ padding: '18px 20px', borderBottom: '1px solid #e2e8f0', background: '#ffffff' }}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
            gap: '12px',
          }}
        >
          {/* 1 Unit */}
          <div
            onClick={() => setSelectedTier('tier_1')}
            style={{
              padding: '14px 16px',
              borderRadius: '8px',
              border: `2px solid ${selectedTier === 'tier_1' ? '#2563eb' : '#e2e8f0'}`,
              background: selectedTier === 'tier_1' ? '#eff6ff' : '#f8fafc',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', fontWeight: 700, color: '#64748b' }}>1 UNIT (PROTOTYPE)</span>
              <span style={{ fontSize: '10.5px', color: '#94a3b8' }}>Baseline</span>
            </div>
            <div style={{ fontSize: '22px', fontWeight: 800, color: '#0f172a', margin: '4px 0' }}>
              ${summary.board_cost_1?.toFixed(2) || '0.00'}
            </div>
            <div style={{ fontSize: '11px', color: '#64748b' }}>
              Batch Total: <strong>${summary.batch_cost_1?.toFixed(2) || '0.00'}</strong>
            </div>
          </div>

          {/* 25 Units */}
          <div
            onClick={() => setSelectedTier('tier_25')}
            style={{
              padding: '14px 16px',
              borderRadius: '8px',
              border: `2px solid ${selectedTier === 'tier_25' ? '#2563eb' : '#e2e8f0'}`,
              background: selectedTier === 'tier_25' ? '#eff6ff' : '#f8fafc',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', fontWeight: 700, color: '#64748b' }}>25 UNITS (PILOT RUN)</span>
              <span style={{ fontSize: '10.5px', color: '#059669', fontWeight: 600 }}>
                {summary.board_cost_1 ? `-${(((summary.board_cost_1 - summary.board_cost_25) / summary.board_cost_1) * 100).toFixed(0)}%` : ''}
              </span>
            </div>
            <div style={{ fontSize: '22px', fontWeight: 800, color: '#0f172a', margin: '4px 0' }}>
              ${summary.board_cost_25?.toFixed(2) || '0.00'}
            </div>
            <div style={{ fontSize: '11px', color: '#64748b' }}>
              Batch Total: <strong>${summary.batch_cost_25?.toFixed(2) || '0.00'}</strong>
            </div>
          </div>

          {/* 100 Units */}
          <div
            onClick={() => setSelectedTier('tier_100')}
            style={{
              padding: '14px 16px',
              borderRadius: '8px',
              border: `2px solid ${selectedTier === 'tier_100' ? '#2563eb' : '#e2e8f0'}`,
              background: selectedTier === 'tier_100' ? '#eff6ff' : '#f8fafc',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', fontWeight: 700, color: '#64748b' }}>100 UNITS (PRE-PROD)</span>
              <span style={{ fontSize: '10.5px', color: '#059669', fontWeight: 600 }}>
                {summary.board_cost_1 ? `-${(((summary.board_cost_1 - summary.board_cost_100) / summary.board_cost_1) * 100).toFixed(0)}%` : ''}
              </span>
            </div>
            <div style={{ fontSize: '22px', fontWeight: 800, color: '#0f172a', margin: '4px 0' }}>
              ${summary.board_cost_100?.toFixed(2) || '0.00'}
            </div>
            <div style={{ fontSize: '11px', color: '#64748b' }}>
              Batch Total: <strong>${summary.batch_cost_100?.toFixed(2) || '0.00'}</strong>
            </div>
          </div>

          {/* 1,000 Units */}
          <div
            onClick={() => setSelectedTier('tier_1000')}
            style={{
              padding: '14px 16px',
              borderRadius: '8px',
              border: `2px solid ${selectedTier === 'tier_1000' ? '#059669' : '#bbf7d0'}`,
              background: selectedTier === 'tier_1000' ? '#ecfdf5' : '#f0fdf4',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', fontWeight: 700, color: '#15803d' }}>1,000 UNITS (VOLUME)</span>
              <span style={{ fontSize: '11px', color: '#15803d', fontWeight: 800, background: '#dcfce7', padding: '1px 6px', borderRadius: '4px' }}>
                -{summary.volume_savings_pct?.toFixed(1)}% SAVINGS
              </span>
            </div>
            <div style={{ fontSize: '22px', fontWeight: 800, color: '#047857', margin: '4px 0' }}>
              ${summary.board_cost_1000?.toFixed(2) || '0.00'}
            </div>
            <div style={{ fontSize: '11px', color: '#166534' }}>
              Batch Total: <strong>${summary.batch_cost_1000?.toFixed(2) || '0.00'}</strong>
            </div>
          </div>
        </div>
      </div>

      {/* 4. Analytics Section: Pareto Cost Drivers & Category Spend */}
      <div
        style={{
          padding: '18px 20px',
          borderBottom: '1px solid #e2e8f0',
          background: '#f8fafc',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '20px',
        }}
      >
        {/* Pareto Cost Drivers */}
        <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: '6px', padding: '14px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <TrendingDown size={16} color="#2563eb" />
              <h4 style={{ fontSize: '12.5px', fontWeight: 700, color: '#0f172a', margin: 0 }}>
                Top Pareto Cost Drivers (1,000 Units)
              </h4>
            </div>
            <span style={{ fontSize: '10.5px', color: '#64748b' }}>Top contributors to BOM cost</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {topDrivers.slice(0, 5).map((drv) => (
              <div key={drv.rank} style={{ fontSize: '11.5px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
                  <span>
                    <strong style={{ color: '#1d4ed8', marginRight: '6px' }}>#{drv.rank} {drv.designator}</strong>
                    <span style={{ color: '#64748b' }}>({drv.mpn})</span>
                  </span>
                  <span style={{ fontWeight: 700, color: '#0f172a' }}>
                    ${drv.cost_1000?.toFixed(2)} ({drv.share_pct}%)
                  </span>
                </div>
                <div style={{ width: '100%', height: '6px', background: '#e2e8f0', borderRadius: '3px', overflow: 'hidden' }}>
                  <div
                    style={{
                      width: `${drv.share_pct * 2}%`,
                      maxWidth: '100%',
                      height: '100%',
                      background: drv.rank === 1 ? '#2563eb' : drv.rank === 2 ? '#3b82f6' : '#60a5fa',
                      borderRadius: '3px',
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Category Spend Breakdown */}
        <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: '6px', padding: '14px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <BarChart2 size={16} color="#059669" />
              <h4 style={{ fontSize: '12.5px', fontWeight: 700, color: '#0f172a', margin: 0 }}>
                Spend Breakdown by Category
              </h4>
            </div>
            <span style={{ fontSize: '10.5px', color: '#64748b' }}>Volume tier (1k)</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {categories.slice(0, 5).map((cat) => (
              <div key={cat.category} style={{ fontSize: '11.5px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
                  <span style={{ fontWeight: 600, color: '#334155' }}>
                    {cat.category} <span style={{ color: '#94a3b8', fontSize: '10.5px' }}>({cat.item_count} pcs)</span>
                  </span>
                  <span style={{ fontWeight: 700, color: '#0f172a' }}>
                    ${cat.total_cost_1000?.toFixed(2)} ({cat.pct_of_total}%)
                  </span>
                </div>
                <div style={{ width: '100%', height: '6px', background: '#e2e8f0', borderRadius: '3px', overflow: 'hidden' }}>
                  <div
                    style={{
                      width: `${cat.pct_of_total}%`,
                      maxWidth: '100%',
                      height: '100%',
                      background: '#10b981',
                      borderRadius: '3px',
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 5. Filter & Search Toolbar */}
      <div
        style={{
          padding: '12px 20px',
          borderBottom: '1px solid #e2e8f0',
          background: '#ffffff',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <div style={{ position: 'relative' }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', top: '9px', color: '#94a3b8' }} />
            <input
              type="text"
              placeholder="Search ref des, MPN, description…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                padding: '6px 12px 6px 30px',
                fontSize: '12px',
                border: '1px solid #cbd5e1',
                borderRadius: '6px',
                outline: 'none',
                width: '240px',
              }}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Filter size={14} color="#64748b" />
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              style={{
                padding: '6px 10px',
                fontSize: '12px',
                border: '1px solid #cbd5e1',
                borderRadius: '6px',
                background: '#ffffff',
                color: '#334155',
                outline: 'none',
              }}
            >
              {uniqueCategories.map((c) => (
                <option key={c} value={c}>
                  {c === 'ALL' ? 'All Categories' : c}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ fontSize: '11.5px', color: '#64748b' }}>
          Showing <strong>{filteredItems.length}</strong> of <strong>{items.length}</strong> items • Active Tier: <strong>{tierQtyMap[selectedTier]} units</strong>
        </div>
      </div>

      {/* 6. Itemized Purchasing Schedule Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', fontSize: '11.5px', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ background: '#f8fafc', borderBottom: '1px solid #cbd5e1', color: '#475569' }}>
              <th style={{ padding: '10px 12px' }}>#</th>
              <th style={{ padding: '10px 12px' }}>Designator</th>
              <th style={{ padding: '10px 12px' }}>Qty</th>
              <th style={{ padding: '10px 12px' }}>MPN</th>
              <th style={{ padding: '10px 12px' }}>Description</th>
              <th style={{ padding: '10px 12px' }}>Category</th>
              <th style={{ padding: '10px 12px' }}>Distributor</th>
              <th style={{ padding: '10px 12px' }}>Lead Time</th>
              <th style={{ padding: '10px 12px' }}>Status</th>
              <th style={{ padding: '10px 12px', textAlign: 'right' }}>Unit Price</th>
              <th style={{ padding: '10px 12px', textAlign: 'right' }}>Ext. Cost</th>
            </tr>
          </thead>
          <tbody>
            {filteredItems.length === 0 ? (
              <tr>
                <td colSpan={11} style={{ padding: '30px', textAlign: 'center', color: '#64748b' }}>
                  No components match the selected filter criteria.
                </td>
              </tr>
            ) : (
              filteredItems.map((it) => {
                const tier = it.pricing_tiers[selectedTier];
                return (
                  <tr key={it.item_num} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '9px 12px', color: '#94a3b8' }}>{it.item_num}</td>
                    <td style={{ padding: '9px 12px', fontWeight: 700, color: '#1d4ed8' }}>{it.designator}</td>
                    <td style={{ padding: '9px 12px', fontWeight: 600 }}>{it.quantity}</td>
                    <td style={{ padding: '9px 12px', fontFamily: 'monospace', color: '#0f172a', fontWeight: 600 }}>
                      {it.mpn}
                    </td>
                    <td style={{ padding: '9px 12px', color: '#475569', maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={it.description}>
                      {it.description}
                    </td>
                    <td style={{ padding: '9px 12px', color: '#64748b' }}>{it.category}</td>
                    <td style={{ padding: '9px 12px', color: '#334155' }}>{it.distributor}</td>
                    <td style={{ padding: '9px 12px', color: '#64748b' }}>{it.lead_time_weeks}</td>
                    <td style={{ padding: '9px 12px' }}>
                      <span
                        style={{
                          fontSize: '10px',
                          fontWeight: 700,
                          padding: '2px 6px',
                          borderRadius: '4px',
                          background: it.lifecycle === 'ACTIVE' ? '#dcfce7' : '#fef9c3',
                          color: it.lifecycle === 'ACTIVE' ? '#15803d' : '#854d0e',
                        }}
                      >
                        {it.lifecycle}
                      </span>
                    </td>
                    <td style={{ padding: '9px 12px', textAlign: 'right', fontFamily: 'monospace' }}>
                      ${tier?.unit_price?.toFixed(2)}
                    </td>
                    <td style={{ padding: '9px 12px', textAlign: 'right', fontWeight: 700, fontFamily: 'monospace', color: '#0f172a' }}>
                      ${tier?.ext_price?.toFixed(2)}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* 7. Disclaimer Footer */}
      <div
        style={{
          padding: '12px 20px',
          background: '#f8fafc',
          borderTop: '1px solid #e2e8f0',
          fontSize: '11px',
          color: '#64748b',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '8px',
        }}
      >
        <span>
          <strong>Engineering Qualification: NOT_EVALUATED.</strong> Analytical price break estimation for design-to-cost evaluation. Does not authorize procurement release or purchasing contracts.
        </span>
        <span style={{ fontFamily: 'monospace', fontSize: '10.5px' }}>
          SHA-256: {pricingData?.sha256?.slice(0, 16)}…
        </span>
      </div>

      {/* 8. Print Preview Modal */}
      {previewModalOpen && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100vw',
            height: '100vh',
            background: 'rgba(5, 7, 13, 0.75)',
            backdropFilter: 'blur(3px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '20px',
          }}
        >
          <div
            style={{
              width: '100%',
              maxWidth: '1040px',
              height: '90vh',
              background: '#ffffff',
              borderRadius: '8px',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              boxShadow: '0 20px 50px rgba(0,0,0,0.3)',
            }}
          >
            <div
              style={{
                padding: '12px 18px',
                background: '#f8fafc',
                borderBottom: '1px solid #e2e8f0',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FileSpreadsheet size={18} color="#059669" />
                <strong style={{ fontSize: '13px', color: '#0f172a' }}>
                  {projectCode} - Production BOM Sourcing & Purchasing Report
                </strong>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <button
                  onClick={() => {
                    const iframe = document.getElementById('bom-report-iframe') as HTMLIFrameElement;
                    if (iframe && iframe.contentWindow) {
                      iframe.contentWindow.print();
                    }
                  }}
                  className="btn btn-primary"
                  style={{ fontSize: '11px', padding: '4px 10px', display: 'flex', alignItems: 'center', gap: '4px' }}
                >
                  <Printer size={12} /> Print / Save as PDF
                </button>
                <button
                  onClick={() => setPreviewModalOpen(false)}
                  style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: '4px' }}
                >
                  <X size={18} color="#64748b" />
                </button>
              </div>
            </div>
            <iframe
              id="bom-report-iframe"
              src={`/api/workspace-file?path=${encodeURIComponent(pricingData?.html_path || '')}`}
              title="BOM Sourcing Schedule Preview"
              style={{ width: '100%', flex: 1, border: 'none' }}
            />
          </div>
        </div>
      )}
    </div>
  );
};
