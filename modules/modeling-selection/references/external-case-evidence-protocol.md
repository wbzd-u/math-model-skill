# External Case and Outstanding-Paper Protocol

Use external historical problems, outstanding papers, and method sources only when a real uncertainty remains about candidate methods, validation, or competition requirements. They help discover structure, counterexamples, and validation strategies; they never replace reasoning about the current problem.

## Retrieval and screening

Query with the subproblem's task role, state/event structure, objective, hard constraints, data granularity, uncertainty, and required outputs. Materials with the same application domain but a different mathematical structure are background only.

Prefer official problem statements, original papers, method originals, and official documentation. Outstanding papers can reveal argument organization and validation design, but their results are neither correctness proofs nor portable evidence.

## Record every external evidence item

- stable source, file or URL, locator, and verification status;
- structure shared with the current task and non-matching prerequisites;
- transferable modeling capability, validation idea, or presentation pattern;
- non-transferable data, parameters, results, conclusions, and problem-specific rules;
- affected `sp-*`, candidate chains, and current-task validation still required.

Write this in `candidate-methods.yaml.evidence_records`. An item known only from a directory, title, or search snippet is unverified, never verified.

## Learn from outstanding papers

- how subproblems form an interpretable capability chain;
- what data and assumptions make a method valid;
- what counterfactual, ablation, error, or robustness checks can distinguish routes;
- how competition constraints affect output and argument order.

Do not extract prose, figures, conclusions, parameters, code, or fixed algorithm combinations. Verify method claims through original theory, official documentation, or the original method section, then express them in the current task's notation.
