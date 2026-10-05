# Final presentation handoff

Open `F1_Wing_Angle_Final_Presentation.pptx` for the editable 18-slide deck.
Use `F1_Wing_Angle_Final_Presentation.pdf` for a portable reading copy.
Each slide includes speaker notes; the complete slide-by-slide talking guide
is `presentation/FINAL_PRESENTATION_GUIDE.md` in the repository.

The presentation is finalized using corrected nominal numerical results.
It is not a claim that the entire original project is submission-ready.
Full native MATLAB/Simulink runtime verification, validated direct-physics
Monte Carlo, and regeneration/acceptance of the complete report/data bundle
remain unfinished. Historical uncertainty and lap figures are not used here.

All five monitored active-aero grids completed 465 cases each (2,325 total).
Including the earlier balanced ideal grid, all six active grids completed
2,790 cases. All 93 fixed-grid cases also completed. Completion receipts and
per-case force/convergence checks are preserved under `docs/verification/`.

Rebuild: `python3 -B scripts/build_final_presentation.py`.
The builder requires all six completed active audit receipts and the fresh
fixed sweep/refinement data; it does not rerun simulations or invent results.

The assembly identity in the slide footer binds the active audit receipts;
it is not a complete-project simulation run ID. Corrected fixed results are
sourced separately from the fixed audit/refinement CSVs. Generated file
hashes and structural/headline checks are in `presentation_verification.json`.

Before presenting, enter your own name, roll number, institution and
supervisor where required. No personal details have been invented.
