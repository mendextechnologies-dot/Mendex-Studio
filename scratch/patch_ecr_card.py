from pathlib import Path

p = Path('desktop/src/components/ECRManagementCard.tsx')
text = p.read_text(encoding='utf-8')

# 1. Update reviewDecision state type
old_state = "const [reviewDecision, setReviewDecision] = useState<'APPROVED' | 'REJECTED' | 'UNDER_REVIEW'>('APPROVED');"
new_state = "const [reviewDecision, setReviewDecision] = useState<'APPROVED' | 'REJECTED' | 'UNDER_REVIEW' | 'IMPLEMENTED'>('APPROVED');"
text = text.replace(old_state, new_state)

# 2. Update handleApplyECO
old_apply = """  // Handle Apply Schematic & Forward Annotate PCB
  const handleApplyECO = async (ecr: ECRItem) => {
    setApplyingEcrId(ecr.ecr_id);
    setError(null);
    try {
      const res = await api.applyECRSchematic(ecr.ecr_id, reviewerName, true);
      setEcoResults((prev) => ({ ...prev, [ecr.ecr_id]: res }));
      setSuccessMessage(`ECO successfully applied to schematic & PCB for ${ecr.ecr_number}!`);
      await fetchECRs();
      onRefresh?.();
      setTimeout(() => setSuccessMessage(null), 6000);
    } catch (e: any) {
      setError(e.message || 'Failed to apply ECO forward annotation');
    } finally {
      setApplyingEcrId(null);
    }
  };"""

new_apply = """  // Handle Apply Schematic & Forward Annotate PCB
  const handleApplyECO = async (ecr: ECRItem) => {
    if (!ecr.schematic_ops || ecr.schematic_ops.length === 0) {
      setError(`ECR ${ecr.ecr_number} has no automated schematic operations defined. Complete implementation via Review / Sign-off.`);
      return;
    }
    setApplyingEcrId(ecr.ecr_id);
    setError(null);
    try {
      const res = await api.applyECRSchematic(ecr.ecr_id, reviewerName, true);
      if (res && res.success === false) {
        setError(res.error || 'Failed to apply ECO forward annotation');
        return;
      }
      setEcoResults((prev) => ({ ...prev, [ecr.ecr_id]: res }));
      setSuccessMessage(`ECO successfully applied to schematic & PCB for ${ecr.ecr_number}!`);
      await fetchECRs();
      onRefresh?.();
      setTimeout(() => setSuccessMessage(null), 6000);
    } catch (e: any) {
      setError(e.message || 'Failed to apply ECO forward annotation');
    } finally {
      setApplyingEcrId(null);
    }
  };"""
text = text.replace(old_apply.replace('\r\n', '\n'), new_apply.replace('\r\n', '\n'))

# 3. Update button in card
old_btn = """                    {ecr.status === 'APPROVED' && (
                      <button
                        onClick={() => handleApplyECO(ecr)}
                        disabled={isApplying}
                        className="btn btn-primary"
                        style={{
                          fontSize: 11,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 5,
                          background: 'linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%)',
                          border: 'none',
                        }}
                      >
                        {isApplying ? (
                          <>
                            <RotateCcw size={13} className="animate-spin" /> Annotating PCB...
                          </>
                        ) : (
                          <>
                            <Zap size={13} /> Apply ECO to PCB
                          </>
                        )}
                      </button>
                    )}"""

new_btn = """                    {ecr.status === 'APPROVED' && (
                      ecr.schematic_ops && ecr.schematic_ops.length > 0 ? (
                        <button
                          onClick={() => handleApplyECO(ecr)}
                          disabled={isApplying}
                          className="btn btn-primary"
                          style={{
                            fontSize: 11,
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 5,
                            background: 'linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%)',
                            border: 'none',
                          }}
                        >
                          {isApplying ? (
                            <>
                              <RotateCcw size={13} className="animate-spin" /> Annotating PCB...
                            </>
                          ) : (
                            <>
                              <Zap size={13} /> Apply ECO to PCB
                            </>
                          )}
                        </button>
                      ) : (
                        <button
                          onClick={() => {
                            setReviewModalEcr(ecr);
                            setReviewDecision('IMPLEMENTED');
                            setReviewNotes('Manual engineering verification complete; recorded as implemented.');
                          }}
                          className="btn btn-primary"
                          style={{
                            fontSize: 11,
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 5,
                            background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                            border: 'none',
                          }}
                          title="This ECR has no automated CAD operations; complete sign-off manually"
                        >
                          <CheckCircle2 size={13} /> Complete Sign-off
                        </button>
                      )
                    )}"""
text = text.replace(old_btn.replace('\r\n', '\n'), new_btn.replace('\r\n', '\n'))

# 4. Add IMPLEMENTED to select dropdown in review modal
old_select = """                  <option value="APPROVED">✓ APPROVED (Authorizes Schematic / Layout Forward Annotation)</option>
                  <option value="UNDER_REVIEW">⏳ UNDER REVIEW (Needs Additional Engineering Analysis)</option>"""

new_select = """                  <option value="APPROVED">✓ APPROVED (Authorizes Schematic / Layout Forward Annotation)</option>
                  <option value="IMPLEMENTED">✓ IMPLEMENTED (Sign-off as completed & verified)</option>
                  <option value="UNDER_REVIEW">⏳ UNDER REVIEW (Needs Additional Engineering Analysis)</option>"""
text = text.replace(old_select.replace('\r\n', '\n'), new_select.replace('\r\n', '\n'))

p.write_text(text, encoding='utf-8')
print("Successfully patched ECRManagementCard.tsx")
