# Engineering guidelines — revision 0.1

- Store electrical quantities in SI units, with units explicit in field names.
- Record sources and assumptions; illustrative specifications are never approved designs.
- A missing calculation, simulator or physical test is NOT_EVALUATED, never PASS.
- Simulated, calculated and measured evidence must remain distinct and traceable.
- Never infer isolation safety or standards compliance from simulation or PCB DRC.
- HV prototypes require qualified review, a physical test plan and separate authorization.
- Core/material, winding construction, duty limits, temperature and applicable standards must be supplied before transformer design execution.
- Preserve native inputs, logs, exact versions and SHA-256 hashes when run support is added.
